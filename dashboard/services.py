# dashboard/services.py
"""Aggregation helpers for the home dashboard.

All functions are user-scoped and return plain Python data — no querysets —
so they're safe to serialize as JSON for Chart.js.
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from courses.services import forecast_course
from expenses.models import Expense
from routines.models import HabitCheckin


def study_last_days(user, days: int = 14):
    """Return list of (ISO date, minutes studied) for the last `days` days."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)

    # sessions live on each course — flatten via reverse lookups
    rows = (
        user.courses
        .values("sessions__occurred_at__date")
        .annotate(total=Sum("sessions__minutes"))
        .filter(sessions__occurred_at__date__gte=start)
    )
    by_day = {r["sessions__occurred_at__date"]: (r["total"] or 0) for r in rows}

    labels, values = [], []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%b %d"))
        values.append(by_day.get(d, 0))
    return labels, values


def spend_last_days(user, days: int = 30):
    """Return (labels, values) — daily spend for the last `days` days."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    rows = (
        Expense.objects
        .filter(user=user, occurred_at__date__gte=start)
        .values("occurred_at__date")
        .annotate(total=Sum("amount"))
    )
    by_day = {r["occurred_at__date"]: float(r["total"] or 0) for r in rows}

    labels, values = [], []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%b %d"))
        values.append(round(by_day.get(d, 0.0), 2))
    return labels, values


def habit_completion_last_days(user, days: int = 7):
    """Return (labels, percentages) — % of active habits completed per day."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)

    habit_count = user.habits.filter(is_archived=False).count() or 1
    rows = (
        HabitCheckin.objects
        .filter(habit__user=user, day__gte=start)
        .values("day")
        .annotate(total=Sum("id") * 0 + 1)  # count per day
    )
    # simpler: use .count() per day via annotation on a values query
    from django.db.models import Count
    rows = (
        HabitCheckin.objects
        .filter(habit__user=user, day__gte=start)
        .values("day")
        .annotate(c=Count("id"))
    )
    by_day = {r["day"]: r["c"] for r in rows}

    labels, values = [], []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%a"))
        values.append(round(by_day.get(d, 0) / habit_count * 100))
    return labels, values


def top_course_snapshot(user):
    """Return the not-yet-complete course with the soonest predicted finish."""
    candidates = []
    for c in user.courses.filter(is_archived=False):
        f = forecast_course(c)
        if not f.is_complete and f.predicted_finish:
            candidates.append((c, f))
    if not candidates:
        return None
    # sort by soonest finish
    candidates.sort(key=lambda pair: pair[1].predicted_finish)
    return candidates[0]


def this_month_total(user) -> Decimal:
    today = timezone.localdate()
    first = today.replace(day=1)
    return Expense.objects.filter(user=user, occurred_at__date__gte=first)\
        .aggregate(s=Sum("amount"))["s"] or Decimal("0.00")