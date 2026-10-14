from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from .models import Habit, HabitCheckin

User = get_user_model()

class StreakTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="t", password="Aa12345678!", full_name="T")
        self.habit = Habit.objects.create(user=self.user, name="Read", emoji="📚")

    def test_streak_counts_backwards_from_today(self):
        today = timezone.localdate()
        for i in range(3):
            HabitCheckin.objects.create(habit=self.habit, day=today - timedelta(days=i))
        self.assertEqual(self.habit.current_streak(), 3)

    def test_gap_breaks_streak(self):
        today = timezone.localdate()
        HabitCheckin.objects.create(habit=self.habit, day=today)
        HabitCheckin.objects.create(habit=self.habit, day=today - timedelta(days=2))
        self.assertEqual(self.habit.current_streak(), 1)

    def test_no_checkins_means_zero(self):
        self.assertEqual(self.habit.current_streak(), 0)