from django.contrib import admin

# Register your models here.
# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, SecurityQuestion, UserSecurityAnswer, RecoveryCode


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "full_name", "is_active", "is_staff", "date_joined", "last_login")
    search_fields = ("username", "full_name")
    ordering = ("-date_joined",)


admin.site.register(SecurityQuestion)
admin.site.register(UserSecurityAnswer)
admin.site.register(RecoveryCode)