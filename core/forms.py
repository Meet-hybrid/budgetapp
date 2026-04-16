"""
Forms for user authentication, transactions, budgets, and categories.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Transaction, Budget, Category
from django.utils import timezone


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=False)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['amount', 'transaction_type', 'category', 'date', 'description', 'note', 'recurring']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'transaction_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_transaction_type'}),
            'category': forms.Select(attrs={'class': 'form-control', 'id': 'id_category'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short description...'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes...'}),
            'recurring': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        if user:
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(user__isnull=True)
            ).order_by('name')
        self.fields['date'].initial = timezone.now().date()


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'amount', 'month', 'year']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'month': forms.Select(choices=[(i, timezone.datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)],
                                  attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': '2000', 'max': '2100'}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        if user:
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(user__isnull=True)
            ).filter(category_type__in=['expense', 'both']).order_by('name')
        now = timezone.now()
        self.fields['month'].initial = now.month
        self.fields['year'].initial = now.year


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'icon', 'color', 'category_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category name'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '💸'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'category_type': forms.Select(attrs={'class': 'form-control'}),
        }


class TransactionFilterForm(forms.Form):
    MONTH_CHOICES = [('', 'All Months')] + [(i, timezone.datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)]
    TYPE_CHOICES = [('', 'All Types'), ('income', 'Income'), ('expense', 'Expense')]

    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=False,
                                      widget=forms.Select(attrs={'class': 'form-control'}),
                                      empty_label='All Categories')
    transaction_type = forms.ChoiceField(choices=TYPE_CHOICES, required=False,
                                         widget=forms.Select(attrs={'class': 'form-control'}))
    month = forms.ChoiceField(choices=MONTH_CHOICES, required=False,
                              widget=forms.Select(attrs={'class': 'form-control'}))
    year = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Year'}))

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.db.models import Q
        if user:
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=user) | Q(user__isnull=True)
            ).order_by('name')
