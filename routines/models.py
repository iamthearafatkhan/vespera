# routines/models.py
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Habit(models.Model):
    """A habit the user wants to track daily."""

    EMOJI_CHOICES = [
        ("📚", "Study"), ("🏃", "Exercise"), ("💧", "Water"),
        ("🧘", "Meditate"), ("💻", "Code"), ("🛏️", "Sleep early"),
        ("📝", "Journal"), ("🍎", "Eat well"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="habits")
    name = models.CharField(max_length=80)
    emoji = models.CharField(max_length=4, default="📚")
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.emoji} {self.name}"

    def is_done_on(self, day) -> bool:
        """Fast check: does a check-in exist for this specific day?"""
        return self.checkins.filter(day=day).exists()

    def current_streak(self) -> int:
        """How many consecutive days, ending today (or yesterday), have a check-in?"""
        today = timezone.localdate()
        # grab set of days in a single query, walk backwards
        days = set(self.checkins.values_list("day", flat=True))

        # streak can start today OR yesterday — otherwise the day is still open
        if today in days:
            cursor = today
        elif (today - timedelta(days=1)) in days:
            cursor = today - timedelta(days=1)
        else:
            return 0

        streak = 0
        while cursor in days:
            streak += 1
            cursor -= timedelta(days=1)
        return streak


class HabitCheckin(models.Model):
    """One row per habit per day. Unique together — you can't check in twice."""

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name="checkins")
    day = models.DateField(default=timezone.localdate)

    class Meta:
        unique_together = [("habit", "day")]
        ordering = ["-day"]

    def __str__(self):
        return f"{self.habit.name} · {self.day}"


# routines/models.py — append

class ClassEntry(models.Model):
    """A recurring class in the user's weekly timetable."""

    DAY_CHOICES = [(0, "Mon"), (1, "Tue"), (2, "Wed"), (3, "Thu"),
                   (4, "Fri"), (5, "Sat"), (6, "Sun")]

    KIND_CHOICES = [
        ("lecture", "Lecture"),
        ("lab",     "Lab"),
        ("tutorial","Tutorial"),
        ("other",   "Other"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="classes")
    subject = models.CharField(max_length=80)
    day = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=40, blank=True)
    teacher = models.CharField(max_length=80, blank=True)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default="lecture")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["day", "start_time"]

    def __str__(self):
        return f"{self.subject} · {self.get_day_display()} {self.start_time}"


class ImportantDate(models.Model):
    """Exam, CT, assignment deadline — anything with a specific date."""

    KIND_CHOICES = [
        ("exam",       "Exam"),
        ("ct",         "Class Test"),
        ("assignment", "Assignment"),
        ("project",    "Project"),
        ("deadline",   "Deadline"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="important_dates")
    title = models.CharField(max_length=120)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default="exam")
    date = models.DateField()
    time = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    related_course = models.ForeignKey(
        "courses.Course", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="important_dates",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "time"]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.title}"

    @property
    def days_until(self) -> int:
        return (self.date - timezone.localdate()).days

    @property
    def urgency(self) -> str:
        """Rough priority bucket based on days_until and kind."""
        d = self.days_until
        if d < 0:
            return "past"
        if d <= 2:
            return "critical"
        if d <= 7:
            return "soon"
        if d <= 14:
            return "upcoming"
        return "later"