# courses/tests.py
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import Course, StudySession
from .services import forecast_course, simulate_course

User = get_user_model()


class ForecastTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester", password="Aa12345678!", full_name="T"
        )
        self.course = Course.objects.create(
            user=self.user, title="Test", total_minutes=600
        )

    def test_no_signal_returns_no_prediction(self):
        f = forecast_course(self.course)
        self.assertIsNone(f.predicted_finish)

    def test_steady_pace_gives_forecast_with_interval(self):
        for i in range(10):
            StudySession.objects.create(
                course=self.course,
                user=self.user,
                minutes=30,
                occurred_at=timezone.now() - timedelta(days=i),
            )
        f = forecast_course(self.course)
        self.assertIsNotNone(f.predicted_finish)
        self.assertLessEqual(f.earliest_finish, f.predicted_finish)
        self.assertLessEqual(f.predicted_finish, f.latest_finish)

    def test_complete_course_is_flagged(self):
        StudySession.objects.create(
            course=self.course, user=self.user,
            minutes=600, occurred_at=timezone.now(),
        )
        f = forecast_course(self.course)
        self.assertTrue(f.is_complete)
        self.assertEqual(f.progress_pct, 100.0)


class AdvisorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="t", password="Aa12345678!", full_name="T"
        )
        self.course = Course.objects.create(
            user=self.user, title="Test", total_minutes=6000
        )
        for i in range(14):
            StudySession.objects.create(
                course=self.course,
                user=self.user,
                minutes=30,
                occurred_at=timezone.now() - timedelta(days=i),
            )

    def test_more_time_means_earlier_finish(self):
        base = forecast_course(self.course)
        sim = simulate_course(self.course, extra_minutes_per_day=30, weekday_only=True)
        self.assertIsNotNone(sim)
        self.assertLessEqual(sim["days_to_finish"], base.days_to_finish)

    def test_zero_extra_returns_none(self):
        self.assertIsNone(simulate_course(self.course, extra_minutes_per_day=0))