import os
from io import StringIO
from unittest.mock import patch

import pandas as pd
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from aggregate.metadata_onboarding import monitoring_dashboard_config
from aggregate.models import SurveyAccess, SurveyMetadataVersion
from surnasdes26.services.runtime import metadata_sha256


@override_settings(SURVEY_CONTROL_PLANE_ENABLED=True)
class SurveyEventValidationTests(TestCase):
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
        call_command(
            "clone_survey_event_config",
            source="surnasfeb26",
            target="simulasi_dinamis26",
            name="Simulasi Dinamis 2026",
            database_name="dbcs_simulasi_dinamis26_report",
            apply=True,
            stdout=StringIO(),
        )
        self.survey = SurveyAccess.objects.get(code="simulasi_dinamis26")
        source_metadata = SurveyAccess.objects.get(
            code="surnasfeb26"
        ).metadata_versions.get(is_active=True)
        payload = {**source_metadata.payload, "survey": {**source_metadata.payload["survey"]}}
        payload["survey"].update(
            {
                "code": self.survey.code,
                "name": self.survey.name,
                "dictionary_name": "SIMULASI_DINAMIS26_DICT",
            }
        )
        SurveyMetadataVersion.objects.create(
            survey=self.survey,
            version="metadata_v1",
            questionnaire_key="SIMULASI_DINAMIS26_DICT",
            source_database="dbcs_simulasi_dinamis26_report",
            payload=payload,
            sha256=metadata_sha256(payload),
            source_name="simulasi_dinamis26_metadata.json",
            is_active=True,
        )
        self.survey.status = SurveyAccess.Status.VALIDATION
        self.survey.dashboard_config = monitoring_dashboard_config(payload)
        self.survey.save(update_fields=("status", "dashboard_config"))

    def valid_frame(self):
        variables = self.survey.metadata_versions.get(is_active=True).payload["variables"]
        data = {name.upper(): [1, 1] for name in variables}
        data.update({"Q_AC": [1, 2], "H0_ID": [10, 11]})
        return pd.DataFrame(data)

    def run_validation(self, frame, apply=False):
        output = StringIO()
        arguments = {"survey": self.survey.code}
        if apply:
            arguments["apply"] = True
        with patch(
            "aggregate.management.commands.validate_survey_event.read_data_source",
            return_value=frame,
        ):
            call_command("validate_survey_event", stdout=output, **arguments)
        return output.getvalue()

    def test_preview_passes_without_changing_state(self):
        output = self.run_validation(self.valid_frame())
        self.survey.refresh_from_db()
        self.assertIn("Validation result: PASSED", output)
        self.assertEqual(self.survey.validation_state, SurveyAccess.ValidationState.NOT_RUN)

    def test_apply_records_passed_but_keeps_event_inactive(self):
        self.run_validation(self.valid_frame(), apply=True)
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.validation_state, SurveyAccess.ValidationState.PASSED)
        self.assertFalse(self.survey.active)
        self.assertEqual(self.survey.status, SurveyAccess.Status.VALIDATION)
        self.assertTrue(self.survey.validation_fingerprint)

    def test_missing_identity_fails(self):
        frame = self.valid_frame().drop(columns=["Q_AC"])
        with self.assertRaises(CommandError):
            self.run_validation(frame)

    def test_target_difference_is_warning_not_error(self):
        output = self.run_validation(self.valid_frame())
        self.assertIn("Warnings: 1", output)
        self.assertIn("Validation result: PASSED", output)
