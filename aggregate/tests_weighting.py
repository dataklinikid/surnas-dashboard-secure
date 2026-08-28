import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from aggregate.models import SurveyAccess, SurveyWeight, SurveyWeightSet
from aggregate.weighting import (
    INTERNAL_WEIGHT_COLUMN,
    audit_weight_frame,
    fingerprint_dataset,
    resolve_weighting,
)


class WeightAuditTests(TestCase):
    def setUp(self):
        self.dataset = pd.DataFrame({"Q_AC": ["RESP001", "RESP002", "RESP003"]})

    def test_complete_positive_weights_pass(self):
        frame = pd.DataFrame(
            {"Q_AC": ["RESP001", "RESP002", "RESP003"], "WEIGHT": [0.8, 1.0, 1.2]}
        )
        result = audit_weight_frame(
            self.dataset,
            frame,
            key_column="Q_AC",
            weight_column="WEIGHT",
        )
        self.assertEqual(result["coverage"], 100.0)
        self.assertEqual(result["errors"], [])
        self.assertAlmostEqual(result["weight_sum"], 3.0)

    def test_duplicate_and_nonpositive_weights_fail(self):
        frame = pd.DataFrame(
            {"Q_AC": ["RESP001", "RESP001", "RESP003"], "WEIGHT": [1.0, 1.1, 0]}
        )
        result = audit_weight_frame(
            self.dataset,
            frame,
            key_column="Q_AC",
            weight_column="WEIGHT",
        )
        self.assertGreater(result["duplicate_key_count"], 0)
        self.assertEqual(result["non_positive_count"], 1)
        self.assertTrue(result["errors"])


class WeightCommandTests(TestCase):
    def setUp(self):
        SurveyAccess.objects.update_or_create(
            code="surnasfeb26",
            defaults={"name": "Surnas", "active": True},
        )
        self.dataset = pd.DataFrame({"Q_AC": ["1", "2", "3", "4"]})

    def _csv(self):
        temporary = tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8")
        temporary.write("Q_AC,WEIGHT\n1,0.8\n2,0.9\n3,1.1\n4,1.2\n")
        temporary.close()
        self.addCleanup(lambda: Path(temporary.name).unlink(missing_ok=True))
        return temporary.name

    @patch("aggregate.management.commands.import_survey_weights.get_dataset")
    def test_preview_does_not_write(self, mocked_dataset):
        mocked_dataset.return_value = self.dataset
        output = StringIO()
        call_command(
            "import_survey_weights",
            survey_code="surnasfeb26",
            file=self._csv(),
            weight_version="raking_v1",
            stdout=output,
        )
        self.assertIn("Coverage: 100.0000%", output.getvalue())
        self.assertEqual(SurveyWeightSet.objects.count(), 0)

    @patch("aggregate.management.commands.import_survey_weights.get_dataset")
    def test_apply_stores_inactive_version(self, mocked_dataset):
        mocked_dataset.return_value = self.dataset
        call_command(
            "import_survey_weights",
            survey_code="surnasfeb26",
            file=self._csv(),
            weight_version="raking_v1",
            apply=True,
        )
        weight_set = SurveyWeightSet.objects.get(version="raking_v1")
        self.assertFalse(weight_set.is_active)
        self.assertEqual(SurveyWeight.objects.filter(weight_set=weight_set).count(), 4)

    @patch("aggregate.management.commands.activate_survey_weights.get_dataset")
    def test_activation_rejects_changed_dataset(self, mocked_dataset):
        survey = SurveyAccess.objects.get(code="surnasfeb26")
        weight_set = SurveyWeightSet.objects.create(
            survey=survey,
            version="old",
            method="test",
            key_column="Q_AC",
            weight_column="WEIGHT",
            file_sha256="0" * 64,
            dataset_fingerprint="0" * 64,
            source_row_count=1,
            matched_count=1,
            coverage=100,
            weight_sum=1,
            weight_min=1,
            weight_max=1,
            weight_mean=1,
            effective_sample_size=1,
        )
        SurveyWeight.objects.create(weight_set=weight_set, respondent_key="1", weight=1)
        mocked_dataset.return_value = pd.DataFrame({"Q_AC": ["1", "2"]})

        with self.assertRaises(CommandError):
            call_command(
                "activate_survey_weights",
                survey_code="surnasfeb26",
                weight_version="old",
            )

    @patch("aggregate.management.commands.activate_survey_weights.get_dataset")
    def test_activation_switches_active_version(self, mocked_dataset):
        survey = SurveyAccess.objects.get(code="surnasfeb26")
        mocked_dataset.return_value = self.dataset
        fingerprint = fingerprint_dataset(self.dataset, "Q_AC")
        old_set = self._weight_set(survey, "old", fingerprint, active=True)
        new_set = self._weight_set(survey, "new", fingerprint, active=False)

        call_command(
            "activate_survey_weights",
            survey_code="surnasfeb26",
            weight_version="new",
        )

        old_set.refresh_from_db()
        new_set.refresh_from_db()
        self.assertFalse(old_set.is_active)
        self.assertTrue(new_set.is_active)

    def test_resolve_weighting_attaches_active_weights(self):
        survey = SurveyAccess.objects.get(code="surnasfeb26")
        fingerprint = fingerprint_dataset(self.dataset, "Q_AC")
        self._weight_set(survey, "active", fingerprint, active=True)

        weighted, weight_column, status = resolve_weighting(
            self.dataset,
            "surnasfeb26",
            "weighted",
        )

        self.assertEqual(weight_column, INTERNAL_WEIGHT_COLUMN)
        self.assertEqual(weighted[weight_column].sum(), 4.0)
        self.assertTrue(status["valid"])
        self.assertEqual(status["version"], "active")

    def _weight_set(self, survey, version, fingerprint, active):
        weight_set = SurveyWeightSet.objects.create(
            survey=survey,
            version=version,
            method="test",
            key_column="Q_AC",
            weight_column="WEIGHT",
            file_sha256="0" * 64,
            dataset_fingerprint=fingerprint,
            source_row_count=4,
            matched_count=4,
            coverage=100,
            weight_sum=4,
            weight_min=1,
            weight_max=1,
            weight_mean=1,
            effective_sample_size=4,
            is_active=active,
        )
        SurveyWeight.objects.bulk_create(
            [
                SurveyWeight(weight_set=weight_set, respondent_key=key, weight=1)
                for key in ("1", "2", "3", "4")
            ]
        )
        return weight_set
