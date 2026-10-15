# routines/views.py
from datetime import date, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Habit, HabitCheckin

# routines/views.py — add these imports

from .models import Habit, HabitCheckin, ClassEntry, ImportantDate


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




# ---------- Class schedule ----------

def _schedule_grid(user):
    """Return rows for a week: 7 days, each with its classes."""
    days = []
    today = timezone.localdate()
    for d in range(7):
        entries = user.classes.filter(day=d, is_active=True).order_by("start_time")
        days.append({"index": d, "name": ClassEntry.DAY_CHOICES[d][1], "entries": entries})
    return days


@login_required
def schedule(request):
    return render(request, "routines/schedule.html", {
        "week": _schedule_grid(request.user),
        "kinds": ClassEntry.KIND_CHOICES,
    })


@login_required
@require_POST
def class_create(request):
    subject = (request.POST.get("subject") or "").strip()
    day = request.POST.get("day")
    start = request.POST.get("start_time")
    end = request.POST.get("end_time")
    kind = request.POST.get("kind") or "lecture"
    room = (request.POST.get("room") or "").strip()
    teacher = (request.POST.get("teacher") or "").strip()

    if not (subject and day is not None and start and end):
        messages.error(request, "Subject, day, start and end are required.")
        return redirect("routines:schedule")

    ClassEntry.objects.create(
        user=request.user,
        subject=subject,
        day=int(day),
        start_time=start,
        end_time=end,
        kind=kind,
        room=room,
        teacher=teacher,
    )
    messages.success(request, "Class added.")
    return redirect("routines:schedule")


@login_required
@require_POST
def class_delete(request, pk):
    entry = get_object_or_404(ClassEntry, pk=pk, user=request.user)
    entry.delete()
    messages.success(request, "Class removed.")
    return redirect("routines:schedule")


# ---------- Important dates ----------

@login_required
@require_POST
def date_create(request):
    title = (request.POST.get("title") or "").strip()
    kind = request.POST.get("kind") or "exam"
    d = request.POST.get("date")
    t = request.POST.get("time") or None
    course_id = request.POST.get("related_course") or None

    if not (title and d):
        messages.error(request, "Title and date required.")
        return redirect("routines:important_dates")

    ImportantDate.objects.create(
        user=request.user,
        title=title,
        kind=kind,
        date=d,
        time=t,
        related_course_id=course_id,
        notes=(request.POST.get("notes") or "").strip(),
    )
    messages.success(request, "Reminder added.")
    return redirect("routines:important_dates")


@login_required
@require_POST
def date_delete(request, pk):
    item = get_object_or_404(ImportantDate, pk=pk, user=request.user)
    item.delete()
    messages.success(request, "Reminder removed.")
    return redirect("routines:important_dates")


@login_required
def important_dates(request):
    today = timezone.localdate()
    upcoming = request.user.important_dates.filter(date__gte=today).order_by("date", "time")
    past = request.user.important_dates.filter(date__lt=today).order_by("-date")[:10]
    return render(request, "routines/important_dates.html", {
        "upcoming": upcoming,
        "past": past,
        "kinds": ImportantDate.KIND_CHOICES,
        "courses": request.user.courses.filter(is_archived=False),
    })