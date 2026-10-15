# expenses/urls.py
from django.urls import path
from . import views

app_name = "expenses"

urlpatterns = [
    path("", views.expense_list, name="list"),
    path("insights/", views.insights_view, name="insights"),
    path("add/", views.expense_add, name="add"),
    path("budget/", views.set_budget, name="set_budget"),
    path("<int:pk>/delete/", views.expense_delete, name="delete"),
]