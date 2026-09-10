import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from aggregate.models import SurveyAccess
from surnasdes26.services.registry import load_registry


@override_settings(SURVEY_CONTROL_PLANE_ENABLED=True)
class CloneSurveyEventConfigTests(TestCase):
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

    def run_clone(self, apply=False):
        output = StringIO()
        arguments = {
            "source": "surnasfeb26",
            "target": "simulasi_dinamis26",
            "name": "Simulasi Dinamis 2026",
            "database_name": "dbcs_simulasi_dinamis26_report",
        }
        if apply:
            arguments["apply"] = True
        call_command("clone_survey_event_config", stdout=output, **arguments)
        return output.getvalue()

    def test_preview_does_not_create_target(self):
        output = self.run_clone()
        self.assertIn("PREVIEW", output)
        self.assertFalse(SurveyAccess.objects.filter(code="simulasi_dinamis26").exists())

    def test_apply_creates_inactive_postgresql_only_event(self):
        self.run_clone(apply=True)
        target = SurveyAccess.objects.get(code="simulasi_dinamis26")
        self.assertFalse(target.active)
        self.assertEqual(target.status, SurveyAccess.Status.DRAFT)
        self.assertNotIn(target.code, load_registry())
        self.assertEqual(target.memberships.count(), 0)
        self.assertEqual(target.weight_sets.count(), 0)
        self.assertEqual(target.event_type.code, "opinion_survey")
        self.assertEqual(
            set(target.event_modules.filter(enabled=True).values_list("module__code", flat=True)),
            {"fieldwork_monitoring", "survey_analytics", "weighted_analysis"},
        )

    def test_apply_does_not_copy_metadata_or_dashboard_configuration(self):
        self.run_clone(apply=True)
        target = SurveyAccess.objects.get(code="simulasi_dinamis26")
        self.assertFalse(target.metadata_versions.exists())
        self.assertEqual(target.dashboard_config, {})
        self.assertTrue(
            all(
                readiness == "pending"
                for readiness in target.event_modules.values_list("readiness", flat=True)
            )
        )

    def test_existing_target_is_rejected(self):
        self.run_clone(apply=True)
        with self.assertRaises(CommandError):
            self.run_clone(apply=True)
