"""
Management command to populate the database with sample data for testing.
Usage: python manage.py seed_data
"""
import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Category, Transaction, Budget


class Command(BaseCommand):
    help = 'Seed the database with sample data'

    def handle(self, *args, **options):
        # Create test user
        user, created = User.objects.get_or_create(
            username='demo',
            defaults={'email': 'demo@example.com', 'first_name': 'Demo', 'last_name': 'User'}
        )
        if created:
            user.set_password('demo1234')
            user.save()
            self.stdout.write('Created user: demo / demo1234')
        
        # Create categories
        cats = {}
        cat_data = [
            ('Food & Dining', '🍔', '#f59e0b', 'expense'),
            ('Housing & Rent', '🏠', '#ef4444', 'expense'),
            ('Transport', '🚗', '#3b82f6', 'expense'),
            ('Shopping', '🛍️', '#ec4899', 'expense'),
            ('Entertainment', '🎮', '#8b5cf6', 'expense'),
            ('Utilities', '💡', '#f97316', 'expense'),
            ('Health', '💊', '#10b981', 'expense'),
            ('Salary', '💼', '#22c55e', 'income'),
            ('Freelance', '💻', '#a3e635', 'income'),
            ('Investment', '📈', '#84cc16', 'income'),
        ]
        for name, icon, color, ctype in cat_data:
            cat, _ = Category.objects.get_or_create(
                user=user, name=name,
                defaults={'icon': icon, 'color': color, 'category_type': ctype}
            )
            cats[name] = cat

        # Create transactions for last 3 months
        today = date.today()
        income_cats = ['Salary', 'Freelance', 'Investment']
        expense_cats = ['Food & Dining', 'Housing & Rent', 'Transport', 'Shopping', 'Entertainment', 'Utilities', 'Health']

        for i in range(90):
            d = today - timedelta(days=i)
            # Monthly salary
            if d.day == 1:
                Transaction.objects.get_or_create(
                    user=user, date=d, description='Monthly Salary',
                    defaults={'amount': Decimal('5000'), 'transaction_type': 'income', 'category': cats['Salary']}
                )
            # Random expenses
            if random.random() > 0.4:
                cat_name = random.choice(expense_cats)
                amounts = {'Food & Dining': (15, 80), 'Housing & Rent': (800, 800), 'Transport': (10, 50),
                           'Shopping': (20, 200), 'Entertainment': (15, 60), 'Utilities': (80, 150), 'Health': (30, 100)}
                lo, hi = amounts.get(cat_name, (10, 100))
                amount = Decimal(str(round(random.uniform(lo, hi), 2)))
                descs = {'Food & Dining': ['Lunch', 'Dinner', 'Groceries', 'Coffee'],
                         'Transport': ['Uber', 'Bus fare', 'Gas', 'Parking'],
                         'Shopping': ['Amazon', 'Clothing', 'Electronics'],
                         'Entertainment': ['Netflix', 'Cinema', 'Concert'],
                         'Utilities': ['Electric bill', 'Water bill', 'Internet'],
                         'Health': ['Pharmacy', 'Gym', 'Doctor visit'],
                         'Housing & Rent': ['Monthly rent']}
                desc = random.choice(descs.get(cat_name, ['Expense']))
                Transaction.objects.create(user=user, date=d, amount=amount, transaction_type='expense',
                                           category=cats[cat_name], description=desc)

        # Create budgets for current month
        month, year = today.month, today.year
        budget_data = [
            ('Food & Dining', 400), ('Housing & Rent', 1000), ('Transport', 200),
            ('Shopping', 300), ('Entertainment', 150), ('Utilities', 200),
        ]
        for cat_name, amt in budget_data:
            Budget.objects.get_or_create(
                user=user, category=cats[cat_name], month=month, year=year,
                defaults={'amount': Decimal(str(amt))}
            )

        self.stdout.write(self.style.SUCCESS('Sample data created! Login: demo / demo1234'))
