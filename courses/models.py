# courses/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone


class Course(models.Model):
    """A course a user wants to complete. Total length is set by the user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
        # ---- new fields ----
    PLATFORM_CHOICES = [
        ("",             "— No platform —"),
        ("udemy",        "Udemy"),
        ("coursera",     "Coursera"),
        ("edx",          "edX"),
        ("youtube",      "YouTube"),
        ("kaggle",       "Kaggle"),
        ("datacamp",     "DataCamp"),
        ("pluralsight",  "Pluralsight"),
        ("udacity",      "Udacity"),
        ("freecodecamp", "freeCodeCamp"),
        ("book",         "Book"),
        ("university",   "University"),
        ("other",        "Other"),
    ]
    platform = models.CharField(
        max_length=20, choices=PLATFORM_CHOICES, blank=True, default="",
    )
    course_url = models.URLField(blank=True, default="", max_length=500)

    # Store everything as minutes — simpler math, no hour/minute juggling.
    # 147h 11m → 8831
    total_minutes = models.PositiveIntegerField(help_text="Total expected length in minutes")

    # A small accent colour for the card. Cosmetic only.
    color = models.CharField(max_length=16, default="violet")

    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    COLOR_HEX = {
        "violet":  "#8b7bff",
        "teal":    "#2ee7d6",
        "emerald": "#10b981",
        "amber":   "#f5a623",
        "rose":    "#ef4444",
        "slate":   "#64748b",
    }

    @property
    def color_hex(self) -> str:
        """Hex code for this course's accent colour (fallback: pacific blue)."""
        return self.COLOR_HEX.get(self.color, "#58a4b0")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def studied_minutes(self) -> int:
        """Sum of every session's minutes for this course."""
        return self.sessions.aggregate(s=models.Sum("minutes"))["s"] or 0

    @property
    def remaining_minutes(self) -> int:
        """Minutes left. Never below zero (users can over-log)."""
        return max(self.total_minutes - self.studied_minutes, 0)

    @property
    def progress_pct(self) -> float:
        """0..100, safe when total_minutes is zero."""
        if self.total_minutes == 0:
            return 0.0
        return min(self.studied_minutes / self.total_minutes * 100, 100.0)

    @property
    def is_complete(self) -> bool:
        return self.studied_minutes >= self.total_minutes


class StudySession(models.Model):
    """One logged session: 'today I studied 1h 12m'."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    # denormalized user for safety + fast ownership checks
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    minutes = models.PositiveIntegerField()
    notes = models.CharField(max_length=280, blank=True)

    # When the studying actually happened (defaults to now)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            # speeds up the "last 30 days" aggregation we use for forecasting
            models.Index(fields=["course", "occurred_at"]),
        ]

    def __str__(self):
        return f"{self.course.title} · {self.minutes}m"