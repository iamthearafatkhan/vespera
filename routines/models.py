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