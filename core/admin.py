from django.contrib import admin
from .models import Category, Transaction, Budget

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'category_type', 'user']
    list_filter = ['category_type']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'transaction_type', 'category', 'amount', 'description']
    list_filter = ['transaction_type', 'category', 'user']
    search_fields = ['description']

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['user', 'category', 'amount', 'month', 'year']
    list_filter = ['user', 'month', 'year']
