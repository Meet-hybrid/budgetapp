"""
Core models for the BudgetApp:
- Category: Income/Expense categories
- Transaction: Individual financial records
- Budget: Monthly spending limits per category
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal


class Category(models.Model):
    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('both', 'Both'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='💸')
    color = models.CharField(max_length=7, default='#6366f1')
    category_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='both')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return f"{self.icon} {self.name}"


class Transaction(models.Model):
    TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    RECURRING_CHOICES = [
        ('none', 'Not Recurring'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='transactions')
    date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=255, blank=True, default='')
    note = models.TextField(blank=True, default='')
    recurring = models.CharField(max_length=10, choices=RECURRING_CHOICES, default='none')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        symbol = '+' if self.transaction_type == 'income' else '-'
        return f"{symbol}₦{self.amount} - {self.description or str(self.category)}"


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    month = models.IntegerField()
    year = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'category', 'month', 'year']
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.user.username} - {self.category} ({self.month}/{self.year}): ₦{self.amount}"

    def get_spent(self):
        from django.db.models import Sum
        result = Transaction.objects.filter(
            user=self.user, category=self.category,
            transaction_type='expense', date__month=self.month, date__year=self.year,
        ).aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0')

    def get_percentage(self):
        spent = self.get_spent()
        if self.amount == 0:
            return 0
        return min(int((spent / self.amount) * 100), 100)

    def get_remaining(self):
        return self.amount - self.get_spent()

    def get_status(self):
        pct = self.get_percentage()
        if pct >= 100:
            return 'danger'
        elif pct >= 75:
            return 'warning'
        return 'safe'
