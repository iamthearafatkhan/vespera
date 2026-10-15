# routines/urls.py
from django.urls import path
from . import views

app_name = "routines"

urlpatterns = [
    path("", views.habit_board, name="board"),
    path("new/", views.habit_create, name="create"),
    path("<int:habit_id>/toggle/<str:day_iso>/", views.habit_toggle, name="toggle"),
    path("<int:pk>/archive/", views.habit_archive, name="archive"),
    path("schedule/", views.schedule, name="schedule"),
    path("schedule/new/", views.class_create, name="class_create"),
    path("schedule/<int:pk>/delete/", views.class_delete, name="class_delete"),
    path("dates/", views.important_dates, name="important_dates"),
    path("dates/new/", views.date_create, name="date_create"),
    path("dates/<int:pk>/delete/", views.date_delete, name="date_delete"),
]