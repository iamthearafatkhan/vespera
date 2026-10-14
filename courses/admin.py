from django.contrib import admin

# Register your models here.
# courses/admin.py
from django.contrib import admin
from .models import Course, StudySession


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "total_minutes", "is_archived", "created_at")
    list_filter = ("is_archived",)
    search_fields = ("title", "user__username")


@admin.register(StudySession)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("course", "user", "minutes", "occurred_at")
    list_filter = ("course",)