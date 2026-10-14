# accounts/urls.py
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("recovery-codes/", views.recovery_codes, name="recovery_codes"),
    path("reset/", views.reset_step1, name="reset_step1"),
    path("reset/new/", views.reset_step2, name="reset_step2"),
]