# expenses/admin.py
from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "category", "occurred_at")
    list_filter = ("category",)
    search_fields = ("user__username", "description")