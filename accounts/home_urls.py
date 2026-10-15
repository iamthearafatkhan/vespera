# accounts/home_urls.py
from django.shortcuts import redirect, render
from django.urls import path


def home(request):
    """Public entry point.

    Logged-in → dashboard.
    Logged-out → landing page.
    """
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    return render(request, "landing.html")


urlpatterns = [path("", home)]