import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from aggregate.event_validation import event_configuration_signature
from aggregate.models import SurveyAccess


@override_settings(SURVEY_CONTROL_PLANE_ENABLED=True)
class MonitoringConfigurationCommandTests(TestCase):
    def setUp(self):
        with patch.dict(os.environ, {"SURNAS_DB_NAME": "dbcs_source_report"}):
            call_command(
                "sync_survey_event_config",
                survey="surnasfeb26",
                program_code="surnas",
                program_name="Survei Nasional",
                region_code="indonesia",
                region_name="Indonesia",
                region_level="national",
                metadata_version="metadata_v1",
                apply=True,
                stdout=StringIO(),
            )
        self.survey = SurveyAccess.objects.select_related("data_source").get(code="surnasfeb26")
        metadata = self.survey.metadata_versions.get(is_active=True)
        self.survey.dashboard_config = {}
        self.survey.validation_state = SurveyAccess.ValidationState.PASSED
        self.survey.validated_at = timezone.now()
        self.survey.validation_report = {
            "configuration_signature": event_configuration_signature(
                self.survey, self.survey.data_source, metadata
            ),
            "errors": [],
        }
        self.survey.save(
            update_fields=(
                "dashboard_config",
                "validation_state",
                "validated_at",
                "validation_report",
            )
        )

    def test_preview_does_not_change_active_event(self):
        output = StringIO()
        call_command(
            "configure_event_monitoring",
            survey=self.survey.code,
            variable="Q_F",
            stdout=output,
        )
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.dashboard_config, {})
        self.assertIn("PREVIEW", output.getvalue())

    def test_apply_repairs_config_and_preserves_active_state(self):
        old_signature = self.survey.validation_report["configuration_signature"]
        output = StringIO()
        call_command(
            "configure_event_monitoring",
            survey=self.survey.code,
            variable="Q_F",
            label="Distribusi per provinsi",
            apply=True,
            stdout=output,
        )
        self.survey.refresh_from_db()
        self.assertTrue(self.survey.active)
        self.assertEqual(self.survey.dashboard_config["monitoring_group_variable"], "Q_F")
        self.assertNotEqual(
            self.survey.validation_report["configuration_signature"], old_signature
        )
        self.assertEqual(
            self.survey.validation_report["configuration_signature_history"][-1]["previous"],
            old_signature,
        )
        self.assertIn("Read-only reporting database: tidak diubah", output.getvalue())

    def test_unknown_variable_is_rejected(self):
        with self.assertRaises(CommandError):
            call_command(
                "configure_event_monitoring",
                survey=self.survey.code,
                variable="Q_TIDAK_ADA",
                stdout=StringIO(),
            )
