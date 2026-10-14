# expenses/urls.py
from django.urls import path
from . import views

app_name = "expenses"

urlpatterns = [
    path("", views.expense_list, name="list"),
    path("add/", views.expense_add, name="add"),
    path("<int:pk>/delete/", views.expense_delete, name="delete"),
]