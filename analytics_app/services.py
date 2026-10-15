# analytics_app/services.py
"""User activity metrics + ML helpers.

Everything here is read-only. No writes, no migrations.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Max
from django.utils import timezone

User = get_user_model()

# "Active" = logged in within this many days
ACTIVE_WINDOW_DAYS = 7
IDLE_WINDOW_DAYS = 30


def user_activity_breakdown():
    """Return counts of users by activity bucket."""
    now = timezone.now()
    active_cutoff = now - timedelta(days=ACTIVE_WINDOW_DAYS)
    idle_cutoff = now - timedelta(days=IDLE_WINDOW_DAYS)

    total = User.objects.count()
    active = User.objects.filter(last_login__gte=active_cutoff).count()
    # "idle" = hasn't logged in for 30+ days but has logged in before
    idle = User.objects.filter(
        last_login__lt=idle_cutoff, last_login__isnull=False
    ).count()
    # "never" = signed up but never logged in
    never = User.objects.filter(last_login__isnull=True).count()
    # everything else = "recent"
    recent = total - active - idle - never

    return {
        "total": total,
        "active": active,       # last 7 days
        "recent": recent,       # 7–30 days
        "idle": idle,           # 30+ days
        "never": never,         # never logged in
    }


def daily_signups(days: int = 30):
    """Return (labels, counts) — signups per day for the last `days` days."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    rows = (
        User.objects
        .filter(date_joined__date__gte=start)
        .values("date_joined__date")
        .annotate(c=Count("id"))
    )
    by_day = {r["date_joined__date"]: r["c"] for r in rows}
    labels, values = [], []
    for i in range(days):
        d = start + timedelta(days=i)
        labels.append(d.strftime("%b %d"))
        values.append(by_day.get(d, 0))
    return labels, values


def content_per_user():
    """Average courses / habits / expenses per user — a health signal."""
    from courses.models import Course
    from expenses.models import Expense
    from routines.models import Habit

    total = User.objects.count() or 1
    return {
        "courses_per_user": round(Course.objects.count() / total, 2),
        "habits_per_user":  round(Habit.objects.count() / total, 2),
        "expenses_per_user": round(Expense.objects.count() / total, 2),
    }