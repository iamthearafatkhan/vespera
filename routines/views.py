# routines/views.py
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Habit, HabitCheckin


@login_required
def habit_board(request):
    """Weekly grid: rows = habits, cols = last 7 days (oldest→today)."""

    today = timezone.localdate()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]  # 7 days, oldest first

    habits = request.user.habits.filter(is_archived=False)

    # Preload ALL check-ins in this window with ONE query (avoids N+1).
    checkin_set = set(
        HabitCheckin.objects
        .filter(habit__in=habits, day__in=days)
        .values_list("habit_id", "day")
    )

    # build a 2D grid: rows[habit] = list of bools for each day
    rows = []
    for h in habits:
        cells = [(h.id, d, (h.id, d) in checkin_set) for d in days]
        rows.append({"habit": h, "cells": cells, "streak": h.current_streak()})

    return render(request, "routines/board.html", {
        "rows": rows, "days": days, "today": today,
    })


@login_required
@require_POST
def habit_create(request):
    name = (request.POST.get("name") or "").strip()
    emoji = request.POST.get("emoji") or "📚"
    if not name:
        return HttpResponseBadRequest("Name required")
    Habit.objects.create(user=request.user, name=name, emoji=emoji)
    messages.success(request, "Habit added.")
    return redirect("routines:board")


@login_required
@require_POST
def habit_toggle(request, habit_id, day_iso):
    """Flip the check-in state for a habit on a given day."""
    habit = get_object_or_404(Habit, pk=habit_id, user=request.user)

    try:
        day = date.fromisoformat(day_iso)
    except ValueError:
        return HttpResponseBadRequest("Bad date")

    existing = HabitCheckin.objects.filter(habit=habit, day=day).first()
    if existing:
        existing.delete()
        done = False
    else:
        HabitCheckin.objects.create(habit=habit, day=day)
        done = True

    # HTMX partial response — return the updated cell
    return render(request, "routines/_cell.html", {
        "habit": habit, "day": day, "done": done, "today": timezone.localdate(),
    })


@login_required
@require_POST
def habit_archive(request, pk):
    habit = get_object_or_404(Habit, pk=pk, user=request.user)
    habit.is_archived = True
    habit.save(update_fields=["is_archived"])
    return redirect("routines:board")