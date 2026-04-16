# BudgetWise - Personal Finance Manager

A full-stack Django budgeting application for managing personal finances.

## Quick Start

```bash
# 1. Clone / navigate to project
cd budgetapp

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install django

# 4. Run migrations
python manage.py migrate

# 5. Seed sample data (creates demo user)
python manage.py seed_data

# 6. Start server
python manage.py runserver
```

Visit http://127.0.0.1:8000 — Login: `demo` / `demo1234`

## Features
- Auth: register, login, logout
- Dashboard: income/expense summary, charts, budget status
- Transactions: add/edit/delete, filter by date/category/type, CSV export
- Budgets: monthly limits per category with warning indicators
- Categories: custom emoji + color categories
- Reports: monthly charts (doughnut + line), category breakdowns
- Dark mode toggle

## Project Structure
```
budgetapp/
├── core/
│   ├── models.py       # Category, Transaction, Budget
│   ├── views.py        # All view logic
│   ├── forms.py        # Form classes
│   ├── urls.py         # URL routing
│   ├── admin.py        # Admin registration
│   └── management/commands/seed_data.py
├── templates/
│   ├── base.html
│   └── core/           # dashboard, transactions, budgets, categories, reports
├── budgetapp/
│   ├── settings.py
│   └── urls.py
└── db.sqlite3
```
