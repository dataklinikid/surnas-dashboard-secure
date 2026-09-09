from io import StringIO
from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from aggregate.models import (
    EventModuleDefinition,
    EventType,
    Region,
    SurveyAccess,
    SurveyConnectionProfile,
    SurveyDataSource,
    SurveyEventModule,
    SurveyMetadataVersion,
    SurveyMembership,
    SurveyProgram,
)
from surnasdes26.services.runtime import metadata_sha256


class FinalValidationUITests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="validation_admin",
            password="test-password",
            is_staff=True,
        )
        self.regular = get_user_model().objects.create_user(
            username="validation_regular",
            password="test-password",
        )
        program = SurveyProgram.objects.create(code="validasi_program", name="Validasi Program")
        region = Region.objects.create(
            code="validasi_region",
            name="Validasi Region",
            level=Region.Level.OTHER,
        )
        profile = SurveyConnectionProfile.objects.create(
            code="validasi_profile",
            name="Validasi Profile",
            environment_prefix="VALIDASI_DB",
        )
        self.survey = SurveyAccess.objects.create(
            code="validasi_uji27",
            name="Validasi Uji 2027",
            event_type=EventType.objects.get(code="opinion_survey"),
            program=program,
            region=region,
            status=SurveyAccess.Status.VALIDATION,
            dashboard_config={
                "monitoring_group_variable": "Q_B",
                "monitoring_group_label": "Distribusi uji",
            },
            active=False,
        )
        SurveyDataSource.objects.create(
            survey=self.survey,
            connection_profile=profile,
            connection_alias=profile.code,
            environment_prefix=profile.environment_prefix,
            database_name="dbcs_validasi_report",
            table_name="h0",
            identity_column="Q_AC",
            latest_id_column="H0_ID",
            target_n=2,
        )
        payload = {
            "metadata_schema_version": 1,
            "survey": {
                "code": self.survey.code,
                "name": self.survey.name,
                "dictionary_name": "VALIDASI_UI_DICT",
                "source_table": "h0",
                "aggregate_only": True,
            },
            "variables": {
                "Q_B": {"label": "Uji", "section": "Uji", "values": {"1": "Ya"}}
            },
            "multiple_answer_groups": {},
            "build_report": {"contains_respondent_rows": False},
        }
        SurveyMetadataVersion.objects.create(
            survey=self.survey,
            version="metadata_v1",
            questionnaire_key="VALIDASI_UI_DICT",
            source_database="dbcs_validasi_report",
            payload=payload,
            sha256=metadata_sha256(payload),
            is_active=True,
        )
        for code in ("fieldwork_monitoring", "survey_analytics", "weighted_analysis"):
            SurveyEventModule.objects.create(
                survey=self.survey,
                module=EventModuleDefinition.objects.get(code=code),
                readiness=SurveyEventModule.Readiness.PENDING,
            )
        SurveyMembership.objects.create(
            survey=self.survey,
            user=self.staff,
            can_monitor=True,
            can_analyse=True,
            can_export=True,
        )

    def url(self):
        return reverse("aggregate:event_final_validation", args=(self.survey.code,))

    @staticmethod
    def valid_frame():
        return pd.DataFrame(
            {
                "Q_AC": [1, 1, 2],
                "H0_ID": [10, 11, 12],
                "Q_B": [1, 2, 1],
            }
        )

    def run_ui_validation(self, frame):
        self.client.force_login(self.staff)
        with patch(
            "aggregate.management.commands.validate_survey_event.read_data_source",
            return_value=frame,
        ):
            return self.client.post(self.url())

    def test_regular_user_cannot_open_validation(self):
        self.client.force_login(self.regular)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 302)

    def test_valid_dataset_records_report_and_module_readiness(self):
        response = self.run_ui_validation(self.valid_frame())
        self.assertEqual(response.status_code, 200)
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.validation_state, SurveyAccess.ValidationState.PASSED)
        self.assertFalse(self.survey.active)
        self.assertEqual(self.survey.validation_report["raw_rows"], 3)
        self.assertEqual(self.survey.validation_report["final_rows"], 2)
        self.assertEqual(self.survey.validation_report["duplicate_before"], 2)
        self.assertEqual(self.survey.validation_report["duplicate_after"], 0)
        self.assertTrue(self.survey.validation_report["dataset_fingerprint"])
        readiness = dict(
            self.survey.event_modules.values_list("module__code", "readiness")
        )
        self.assertEqual(readiness["fieldwork_monitoring"], "ready")
        self.assertEqual(readiness["survey_analytics"], "ready")
        self.assertEqual(readiness["weighted_analysis"], "pending")
        self.assertContains(response, "Belum ada weight set aktif")

    def test_failed_dataset_blocks_modules_and_keeps_event_inactive(self):
        frame = pd.DataFrame({"Q_AC": ["", "2"], "H0_ID": [10, 11], "Q_B": [1, 1]})
        response = self.run_ui_validation(frame)
        self.assertEqual(response.status_code, 200)
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.validation_state, SurveyAccess.ValidationState.FAILED)
        self.assertFalse(self.survey.active)
        self.assertFalse(
            self.survey.event_modules.exclude(readiness=SurveyEventModule.Readiness.BLOCKED).exists()
        )

    def test_activation_gate_rejects_enabled_pending_module(self):
        self.run_ui_validation(self.valid_frame())
        with self.assertRaises(CommandError):
            call_command("activate_survey_event", survey=self.survey.code, stdout=StringIO())

    def test_derived_readiness_change_does_not_invalidate_signature(self):
        weighted = self.survey.event_modules.get(module__code="weighted_analysis")
        weighted.enabled = False
        weighted.save(update_fields=("enabled", "updated_at"))
        self.run_ui_validation(self.valid_frame())
        call_command("activate_survey_event", survey=self.survey.code, stdout=StringIO())
        self.survey.refresh_from_db()
        self.assertFalse(self.survey.active)
