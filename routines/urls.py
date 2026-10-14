# routines/urls.py
from django.urls import path
from . import views

app_name = "routines"

urlpatterns = [
    path("", views.habit_board, name="board"),
    path("new/", views.habit_create, name="create"),
    path("<int:habit_id>/toggle/<str:day_iso>/", views.habit_toggle, name="toggle"),
    path("<int:pk>/archive/", views.habit_archive, name="archive"),
]