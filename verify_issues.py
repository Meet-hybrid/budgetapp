import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budgetapp.settings')
django.setup()
from django.test import Client
from django.contrib.auth.models import User
from core.models import Budget, Category

c = Client()
print('REGISTER GET', c.get('/register/').status_code)
resp = c.post('/register/', {'username': 'testuser', 'email': 'test@example.com', 'password1': 'Password123', 'password2': 'Password123'})
print('REGISTER POST', resp.status_code, resp.url if resp.status_code in (301, 302) else 'no redirect')
print('USER COUNT', User.objects.filter(username='testuser').count())
user, created = User.objects.get_or_create(username='testuser2', defaults={'email': 'test2@example.com'})
if created:
    user.set_password('Password123')
    user.save()
cat = Category.objects.filter(user=user, category_type__in=['expense', 'both']).first()
if not cat:
    cat = Category.objects.filter(user__isnull=True, category_type__in=['expense', 'both']).first()
if not cat:
    cat = Category.objects.create(user=None, name='TestExpense', category_type='expense')
    print('created custom category', cat.pk)
budget = Budget.objects.create(user=user, category=cat, amount=100, month=1, year=2026)
print('created budget', budget.pk)
print('LOGIN', c.login(username='testuser2', password='Password123'))
resp = c.post(f'/budgets/{budget.pk}/delete/')
print('DELETE POST', resp.status_code, resp.url if resp.status_code in (301, 302) else 'no redirect')
print('BUDGET EXISTS', Budget.objects.filter(pk=budget.pk).exists())
