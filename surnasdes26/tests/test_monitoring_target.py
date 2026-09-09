from unittest import TestCase

from surnasdes26.services.monitoring import monitoring_target_progress


class MonitoringTargetTests(TestCase):
    def test_unset_target_is_supported(self):
        self.assertEqual(monitoring_target_progress(800, None), (None, None))

    def test_positive_target_calculates_progress(self):
        self.assertEqual(monitoring_target_progress(800, "1000"), (1000, 80.0))

    def test_zero_or_invalid_target_is_treated_as_unset(self):
        self.assertEqual(monitoring_target_progress(800, 0), (None, None))
        self.assertEqual(monitoring_target_progress(800, "invalid"), (None, None))
