from django.test import TestCase

from .ml import predict_dropout_risk, FEATURE_NAMES
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .insights import generate_insights, _pearson, _series, _study_minutes_by_day

User = get_user_model()


class DropoutRiskTests(TestCase):
    def test_perfect_consistency_low_risk(self):
        # studied yesterday, every day last week, high consistency
        features = [1.0, 3.0, 7.0, 60.0, 0.0, 0.9, 0.8, 20.0]
        r = predict_dropout_risk(features)
        self.assertEqual(len(r.top_drivers), 3)
        self.assertGreater(r.probability, 0.5)

    def test_stalled_user_high_risk(self):
        # hasn't studied in 21 days, no consistency
        features = [0.0, 0.0, 0.0, 0.0, 21.0, 0.0, 0.0, 0.0]
        r = predict_dropout_risk(features)
        self.assertLess(r.probability, 0.5)

    def test_drivers_are_named(self):
        features = [1.0, 2.0, 3.0, 40.0, 1.0, 0.6, 0.4, 10.0]
        r = predict_dropout_risk(features)
        for name, contrib in r.top_drivers:
            self.assertIn(name, FEATURE_NAMES)






class PearsonTests(TestCase):
    def test_perfect_positive(self):
        self.assertAlmostEqual(_pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]), 1.0, places=6)

    def test_perfect_negative(self):
        self.assertAlmostEqual(_pearson([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]), -1.0, places=6)

    def test_degenerate_returns_none(self):
        self.assertIsNone(_pearson([1, 1, 1], [1, 2, 3]))


class InsightTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="t", password="Aa12345678!", full_name="T")

    def test_no_data_yields_no_insights(self):
        self.assertEqual(generate_insights(self.u), [])