# analytics_app/urls.py
from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.metrics_home, name="metrics"),
]