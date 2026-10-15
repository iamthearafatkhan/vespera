# dashboard/views.py
from routines.models import ImportantDate
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from analytics_app.features import build_features_for_user
from analytics_app.ml import predict_dropout_risk
from analytics_app.insights import generate_insights

from . import services


def home(request):
    """Public landing for anonymous users. Dashboard for logged-in users."""

    # ---- anonymous → landing page ----
    if not request.user.is_authenticated:
        return render(request, "landing.html")

    # ---- logged-in → dashboard ----
    study_labels, study_values = services.study_last_days(request.user, days=14)
    spend_labels, spend_values = services.spend_last_days(request.user, days=30)
    habit_labels, habit_values = services.habit_completion_last_days(request.user, days=7)
    hero = services.top_course_snapshot(request.user)

    active_courses = request.user.courses.filter(is_archived=False).count()
    active_habits  = request.user.habits.filter(is_archived=False).count()
    month_spend    = services.this_month_total(request.user)
    week_study     = sum(study_values[-7:])

    risk = predict_dropout_risk(build_features_for_user(request.user))
    insights = generate_insights(request.user, limit=3)
    today = timezone.localdate()
    upcoming_dates = (
        request.user.important_dates
        .filter(date__gte=today, date__lte=today + timedelta(days=14))
        .order_by("date")[:5]
    )

    return render(request, "dashboard/home.html", {
        "study_labels": study_labels,
        "study_values": study_values,
        "spend_labels": spend_labels,
        "spend_values": spend_values,
        "habit_labels": habit_labels,
        "habit_values": habit_values,

        "hero_course": hero[0] if hero else None,
        "hero_forecast": hero[1] if hero else None,

        "stats": {
            "active_courses": active_courses,
            "active_habits": active_habits,
            "month_spend": month_spend,
            "week_study_hours": round(week_study / 60, 1),
        },
        "risk": risk,
        "insights": insights,
    })