from django.shortcuts import render

# Create your views here.
# courses/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import CourseForm, StudySessionForm
from .models import Course
from .services import forecast_course
from .services import forecast_course, simulate_course


def _get_user_course_or_404(request, pk) -> Course:
    """Ownership check — users can only touch their own courses."""
    return get_object_or_404(Course, pk=pk, user=request.user)


@login_required
def course_list(request):
    """Dashboard of all courses, each with its forecast."""
    courses = request.user.courses.filter(is_archived=False)
    # attach forecast to each — cheap (one query per course, fine at this scale)
    data = [(c, forecast_course(c)) for c in courses]
    return render(request, "courses/list.html", {"rows": data})


@login_required
@require_http_methods(["GET", "POST"])
def course_create(request):
    form = CourseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        course = form.save(commit=False)
        course.user = request.user
        course.save()
        messages.success(request, f"“{course.title}” added.")
        return redirect("courses:detail", pk=course.pk)
    return render(request, "courses/form.html", {"form": form, "mode": "create"})


@login_required
@require_http_methods(["GET", "POST"])
def course_edit(request, pk):
    course = _get_user_course_or_404(request, pk)
    form = CourseForm(request.POST or None, instance=course)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Course updated.")
        return redirect("courses:detail", pk=course.pk)
    return render(request, "courses/form.html", {"form": form, "mode": "edit", "course": course})


@login_required
def course_detail(request, pk):
    """Single course view — big forecast card + session log + history."""
    course = _get_user_course_or_404(request, pk)
    forecast = forecast_course(course)
    sessions = course.sessions.all()[:30]     # recent 30 entries
    form = StudySessionForm()
    return render(request, "courses/detail.html", {
        "course": course, "forecast": forecast, "sessions": sessions, "form": form,
    })


@login_required
@require_http_methods(["POST"])
def log_session(request, pk):
    """Handles the 'add session' form. Responds with HTMX fragment if requested."""
    course = _get_user_course_or_404(request, pk)
    form = StudySessionForm(request.POST)
    if form.is_valid():
        form.save(course=course, user=request.user)
        messages.success(request, "Session logged.")
    else:
        messages.error(request, "Could not save session. Check the values.")

    # If HTMX called us, swap the forecast + history in place.
    if request.headers.get("HX-Request"):
        forecast = forecast_course(course)
        sessions = course.sessions.all()[:30]
        return render(request, "courses/_forecast_and_history.html", {
            "course": course, "forecast": forecast, "sessions": sessions,
            "form": StudySessionForm(),
        })
    return redirect("courses:detail", pk=course.pk)


@login_required
@require_http_methods(["POST"])
def archive_course(request, pk):
    course = _get_user_course_or_404(request, pk)
    course.is_archived = True
    course.save(update_fields=["is_archived"])
    messages.success(request, "Course archived.")
    return redirect("courses:list")



@login_required
def advisor(request, pk):
    """HTMX endpoint — returns the advisor result fragment."""
    course = _get_user_course_or_404(request, pk)

    try:
        extra = int(request.GET.get("extra", 0))
    except (TypeError, ValueError):
        extra = 0
    extra = max(0, min(extra, 120))                          # cap at 2h

    weekday_only = request.GET.get("weekday_only", "1") == "1"

    baseline = forecast_course(course)
    simulated = simulate_course(course, extra, weekday_only)

    # delta in days — negative means "finishes sooner"
    delta_days = None
    if baseline.predicted_finish and simulated:
        delta_days = (simulated["predicted_finish"] - baseline.predicted_finish).days

    return render(request, "courses/_advisor.html", {
        "course": course,
        "baseline": baseline,
        "simulated": simulated,
        "extra": extra,
        "weekday_only": weekday_only,
        "delta_days": delta_days,
    })