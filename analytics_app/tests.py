from django.test import TestCase

from .ml import predict_dropout_risk, FEATURE_NAMES


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