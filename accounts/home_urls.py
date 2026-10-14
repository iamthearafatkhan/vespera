# accounts/home_urls.py
from django.urls import path
from django.shortcuts import redirect

def home(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")
    return redirect("accounts:login")

urlpatterns = [path("", home)]