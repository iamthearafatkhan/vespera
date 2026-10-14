# routines/admin.py
from django.contrib import admin
from .models import Habit, HabitCheckin


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ("name", "emoji", "user", "is_archived", "created_at")


@admin.register(HabitCheckin)
class CheckinAdmin(admin.ModelAdmin):
    list_display = ("habit", "day")