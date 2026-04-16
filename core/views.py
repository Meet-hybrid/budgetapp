"""
Views for BudgetApp - handles dashboard, transactions, budgets, categories,
authentication, reporting, and CSV export.
"""
import csv
import json
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from .forms import (RegisterForm, LoginForm, TransactionForm,
                    BudgetForm, CategoryForm, TransactionFilterForm)
from .models import Transaction, Category, Budget


# ─── Authentication ───────────────────────────────────────────────────────────

def register_view(request):
    """User registration."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            _create_default_categories(user)
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account has been created.')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'core/auth/register.html', {'form': form})


def login_view(request):
    """User login."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect(request.GET.get('next', 'dashboard'))
    else:
        form = LoginForm()
    return render(request, 'core/auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


def _create_default_categories(user):
    """Create default income/expense categories for a new user."""
    defaults = [
        ('Food & Dining', '🍔', '#f59e0b', 'expense'),
        ('Housing & Rent', '🏠', '#ef4444', 'expense'),
        ('Transport', '🚗', '#3b82f6', 'expense'),
        ('Shopping', '🛍️', '#ec4899', 'expense'),
        ('Health', '💊', '#10b981', 'expense'),
        ('Entertainment', '🎮', '#8b5cf6', 'expense'),
        ('Education', '📚', '#06b6d4', 'expense'),
        ('Utilities', '💡', '#f97316', 'expense'),
        ('Savings', '💰', '#14b8a6', 'both'),
        ('Salary', '💼', '#22c55e', 'income'),
        ('Freelance', '💻', '#a3e635', 'income'),
        ('Investment', '📈', '#84cc16', 'income'),
        ('Other Income', '💵', '#4ade80', 'income'),
        ('Other Expense', '💸', '#94a3b8', 'expense'),
    ]
    for name, icon, color, ctype in defaults:
        Category.objects.get_or_create(
            user=user, name=name,
            defaults={'icon': icon, 'color': color, 'category_type': ctype}
        )


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """Main dashboard with summary, recent transactions, and budget overview."""
    now = timezone.now()
    month, year = now.month, now.year

    # Summary totals for current month
    month_txns = Transaction.objects.filter(user=request.user, date__month=month, date__year=year)
    total_income = month_txns.filter(transaction_type='income').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_expense = month_txns.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    balance = total_income - total_expense

    # All-time balance
    all_income = Transaction.objects.filter(user=request.user, transaction_type='income').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    all_expense = Transaction.objects.filter(user=request.user, transaction_type='expense').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    net_worth = all_income - all_expense

    # Recent transactions
    recent_txns = Transaction.objects.filter(user=request.user).select_related('category')[:8]

    # Budget overview
    budgets = Budget.objects.filter(user=request.user, month=month, year=year).select_related('category')
    budget_data = []
    for b in budgets:
        spent = b.get_spent()
        budget_data.append({
            'budget': b, 'spent': spent,
            'percentage': b.get_percentage(), 'status': b.get_status(),
            'remaining': b.get_remaining(),
        })

    # Expense by category for pie chart
    cat_expenses = month_txns.filter(transaction_type='expense').values(
        'category__name', 'category__color', 'category__icon'
    ).annotate(total=Sum('amount')).order_by('-total')[:8]

    # Last 6 months trend
    trend_data = _get_monthly_trend(request.user, 6)

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'net_worth': net_worth,
        'recent_txns': recent_txns,
        'budget_data': budget_data,
        'cat_expenses_json': json.dumps([{
            'label': f"{x['category__icon'] or ''} {x['category__name'] or 'Uncategorized'}",
            'value': float(x['total']),
            'color': x['category__color'] or '#6366f1',
        } for x in cat_expenses]),
        'trend_json': json.dumps(trend_data),
        'current_month': now.strftime('%B %Y'),
    }
    return render(request, 'core/dashboard.html', context)


def _get_monthly_trend(user, months=6):
    """Get income vs expense for the last N months."""
    now = timezone.now()
    data = {'labels': [], 'income': [], 'expense': []}
    for i in range(months - 1, -1, -1):
        m = (now.month - i - 1) % 12 + 1
        y = now.year - ((now.month - i - 1) // 12)
        label = date(y, m, 1).strftime('%b %Y')
        txns = Transaction.objects.filter(user=user, date__month=m, date__year=y)
        inc = txns.filter(transaction_type='income').aggregate(t=Sum('amount'))['t'] or 0
        exp = txns.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or 0
        data['labels'].append(label)
        data['income'].append(float(inc))
        data['expense'].append(float(exp))
    return data


# ─── Transactions ─────────────────────────────────────────────────────────────

@login_required
def transaction_list(request):
    """List all transactions with filtering."""
    txns = Transaction.objects.filter(user=request.user).select_related('category')
    form = TransactionFilterForm(user=request.user, data=request.GET or None)

    if form.is_valid():
        if form.cleaned_data.get('date_from'):
            txns = txns.filter(date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data.get('date_to'):
            txns = txns.filter(date__lte=form.cleaned_data['date_to'])
        if form.cleaned_data.get('category'):
            txns = txns.filter(category=form.cleaned_data['category'])
        if form.cleaned_data.get('transaction_type'):
            txns = txns.filter(transaction_type=form.cleaned_data['transaction_type'])
        if form.cleaned_data.get('month'):
            txns = txns.filter(date__month=form.cleaned_data['month'])
        if form.cleaned_data.get('year'):
            txns = txns.filter(date__year=form.cleaned_data['year'])

    total_income = txns.filter(transaction_type='income').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_expense = txns.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or Decimal('0')

    return render(request, 'core/transactions/list.html', {
        'transactions': txns,
        'filter_form': form,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
    })


@login_required
def transaction_create(request):
    """Create a new transaction."""
    if request.method == 'POST':
        form = TransactionForm(user=request.user, data=request.POST)
        if form.is_valid():
            txn = form.save(commit=False)
            txn.user = request.user
            txn.save()
            messages.success(request, 'Transaction added successfully!')
            return redirect('transaction_list')
    else:
        form = TransactionForm(user=request.user)
    return render(request, 'core/transactions/form.html', {'form': form, 'title': 'Add Transaction'})


@login_required
def transaction_edit(request, pk):
    """Edit an existing transaction."""
    txn = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TransactionForm(user=request.user, data=request.POST, instance=txn)
        if form.is_valid():
            form.save()
            messages.success(request, 'Transaction updated!')
            return redirect('transaction_list')
    else:
        form = TransactionForm(user=request.user, instance=txn)
    return render(request, 'core/transactions/form.html', {'form': form, 'title': 'Edit Transaction', 'transaction': txn})


@login_required
def transaction_delete(request, pk):
    """Delete a transaction."""
    txn = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        txn.delete()
        messages.success(request, 'Transaction deleted.')
        return redirect('transaction_list')
    return render(request, 'core/transactions/confirm_delete.html', {'transaction': txn})


# ─── Budgets ──────────────────────────────────────────────────────────────────

@login_required
def budget_list(request):
    """List budgets, optionally filtered by month/year."""
    now = timezone.now()
    month = int(request.GET.get('month', now.month))
    year = int(request.GET.get('year', now.year))

    budgets = Budget.objects.filter(user=request.user, month=month, year=year).select_related('category')
    budget_data = []
    for b in budgets:
        spent = b.get_spent()
        budget_data.append({
            'budget': b, 'spent': spent,
            'percentage': b.get_percentage(), 'status': b.get_status(),
            'remaining': b.get_remaining(),
        })

    months = [(i, date(2000, i, 1).strftime('%B')) for i in range(1, 13)]
    return render(request, 'core/budgets/list.html', {
        'budget_data': budget_data,
        'months': months,
        'selected_month': month,
        'selected_year': year,
        'years': range(now.year - 2, now.year + 2),
    })


@login_required
def budget_create(request):
    if request.method == 'POST':
        form = BudgetForm(user=request.user, data=request.POST)
        if form.is_valid():
            b = form.save(commit=False)
            b.user = request.user
            b.save()
            messages.success(request, 'Budget created!')
            return redirect('budget_list')
    else:
        form = BudgetForm(user=request.user)
    return render(request, 'core/budgets/form.html', {'form': form, 'title': 'Create Budget'})


@login_required
def budget_edit(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    if request.method == 'POST':
        form = BudgetForm(user=request.user, data=request.POST, instance=budget)
        if form.is_valid():
            form.save()
            messages.success(request, 'Budget updated!')
            return redirect('budget_list')
    else:
        form = BudgetForm(user=request.user, instance=budget)
    return render(request, 'core/budgets/form.html', {'form': form, 'title': 'Edit Budget', 'budget': budget})


@login_required
def budget_delete(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    if request.method == 'POST':
        budget.delete()
        messages.success(request, 'Budget deleted.')
        return redirect('budget_list')
    return render(request, 'core/budgets/confirm_delete.html', {'budget': budget})


# ─── Categories ───────────────────────────────────────────────────────────────

@login_required
def category_list(request):
    from django.db.models import Q
    categories = Category.objects.filter(Q(user=request.user) | Q(user__isnull=True)).order_by('name')
    return render(request, 'core/categories/list.html', {'categories': categories})


@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.user = request.user
            cat.save()
            messages.success(request, 'Category created!')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'core/categories/form.html', {'form': form, 'title': 'Add Category'})


@login_required
def category_edit(request, pk):
    cat = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category updated!')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=cat)
    return render(request, 'core/categories/form.html', {'form': form, 'title': 'Edit Category', 'category': cat})


@login_required
def category_delete(request, pk):
    cat = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == 'POST':
        cat.delete()
        messages.success(request, 'Category deleted.')
        return redirect('category_list')
    return render(request, 'core/categories/confirm_delete.html', {'category': cat})


# ─── Reports ──────────────────────────────────────────────────────────────────

@login_required
def reports(request):
    """Monthly summary report with charts."""
    now = timezone.now()
    month = int(request.GET.get('month', now.month))
    year = int(request.GET.get('year', now.year))

    txns = Transaction.objects.filter(user=request.user, date__month=month, date__year=year)
    total_income = txns.filter(transaction_type='income').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_expense = txns.filter(transaction_type='expense').aggregate(t=Sum('amount'))['t'] or Decimal('0')

    # Category breakdown
    expense_by_cat = txns.filter(transaction_type='expense').values(
        'category__name', 'category__color', 'category__icon'
    ).annotate(total=Sum('amount')).order_by('-total')

    income_by_cat = txns.filter(transaction_type='income').values(
        'category__name', 'category__color', 'category__icon'
    ).annotate(total=Sum('amount')).order_by('-total')

    # Daily spending trend
    daily = txns.filter(transaction_type='expense').values('date').annotate(total=Sum('amount')).order_by('date')

    trend = _get_monthly_trend(request.user, 12)

    months = [(i, date(2000, i, 1).strftime('%B')) for i in range(1, 13)]
    return render(request, 'core/reports.html', {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'expense_by_cat': expense_by_cat,
        'income_by_cat': income_by_cat,
        'expense_cat_json': json.dumps([{
            'label': f"{x['category__icon'] or ''} {x['category__name'] or 'Uncategorized'}",
            'value': float(x['total']), 'color': x['category__color'] or '#6366f1',
        } for x in expense_by_cat]),
        'daily_json': json.dumps([{'date': str(d['date']), 'total': float(d['total'])} for d in daily]),
        'trend_json': json.dumps(trend),
        'months': months,
        'selected_month': month,
        'selected_year': year,
        'years': range(now.year - 3, now.year + 1),
        'month_name': date(year, month, 1).strftime('%B %Y'),
    })


# ─── CSV Export ───────────────────────────────────────────────────────────────

@login_required
def export_csv(request):
    """Export all transactions to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Description', 'Recurring', 'Created'])

    txns = Transaction.objects.filter(user=request.user).select_related('category').order_by('-date')
    for t in txns:
        writer.writerow([
            t.date, t.get_transaction_type_display(),
            str(t.category) if t.category else '',
            t.amount, t.description, t.get_recurring_display(), t.created_at.date(),
        ])
    return response
