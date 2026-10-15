# analytics_app/views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from . import services


@staff_member_required
def metrics_home(request):
    """Staff-only dashboard. Not linked from the sidebar — go to /staff/."""
    return render(request, "analytics_app/metrics.html", {
        "activity": services.user_activity_breakdown(),
        "signup_labels": services.daily_signups(30)[0],
        "signup_values": services.daily_signups(30)[1],
        "content": services.content_per_user(),
        "window_active": services.ACTIVE_WINDOW_DAYS,
        "window_idle": services.IDLE_WINDOW_DAYS,
    })