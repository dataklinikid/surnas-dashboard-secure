import os
from io import StringIO
from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from aggregate.models import SurveyAccess, SurveyMembership, SurveyMetadataVersion
from aggregate.metadata_onboarding import monitoring_dashboard_config
from surnasdes26.services.runtime import metadata_sha256


class SurveyEventSetupMixin:
    def setUp(self):
        super().setUp()
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
        payload = source_metadata.payload.copy()
        payload = {**payload, "survey": {**payload["survey"]}}
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
        self.survey.event_modules.filter(module__code="weighted_analysis").update(
            enabled=False
        )

    def valid_frame(self):
        variables = self.survey.metadata_versions.get(is_active=True).payload["variables"]
        data = {name.upper(): [1, 1] for name in variables}
        data.update({"Q_AC": [1, 2], "H0_ID": [10, 11]})
        return pd.DataFrame(data)

    def record_validation(self):
        with patch(
            "aggregate.management.commands.validate_survey_event.read_data_source",
            return_value=self.valid_frame(),
        ):
            call_command(
                "validate_survey_event",
                survey=self.survey.code,
                apply=True,
                stdout=StringIO(),
            )
        owner, _ = get_user_model().objects.get_or_create(username="activation_owner")
        SurveyMembership.objects.get_or_create(
            survey=self.survey,
            user=owner,
            defaults={"can_monitor": True, "can_analyse": True, "can_export": True},
        )


@override_settings(SURVEY_CONTROL_PLANE_ENABLED=True)
class SurveyEventActivationTests(SurveyEventSetupMixin, TestCase):
    def test_activation_rejects_event_before_recorded_validation(self):
        with self.assertRaises(CommandError):
            call_command("activate_survey_event", survey=self.survey.code, stdout=StringIO())

    def test_activation_preview_keeps_event_inactive(self):
        self.record_validation()
        call_command("activate_survey_event", survey=self.survey.code, stdout=StringIO())
        self.survey.refresh_from_db()
        self.assertFalse(self.survey.active)

    def test_activation_apply_activates_event(self):
        self.record_validation()
        call_command(
            "activate_survey_event",
            survey=self.survey.code,
            apply=True,
            stdout=StringIO(),
        )
        self.survey.refresh_from_db()
        self.assertTrue(self.survey.active)
        self.assertEqual(self.survey.status, SurveyAccess.Status.ACTIVE)

    def test_activation_rejects_event_without_operational_membership(self):
        self.record_validation()
        self.survey.memberships.all().delete()
        with self.assertRaises(CommandError):
            call_command("activate_survey_event", survey=self.survey.code, stdout=StringIO())

    def test_activation_rejects_changed_configuration(self):
        self.record_validation()
        source = self.survey.data_source
        source.table_name = "h1"
        source.save(update_fields=("table_name",))
        with self.assertRaises(CommandError):
            call_command("activate_survey_event", survey=self.survey.code, stdout=StringIO())

    def test_activation_rejects_changed_module_configuration(self):
        self.record_validation()
        assignment = self.survey.event_modules.get(module__code="survey_analytics")
        assignment.config = {"standard_outputs": ["frequency", "crosstab"]}
        assignment.save(update_fields=("config", "updated_at"))
        with self.assertRaises(CommandError):
            call_command("activate_survey_event", survey=self.survey.code, stdout=StringIO())


@override_settings(SURVEY_CONTROL_PLANE_ENABLED=True)
class GrantSurveyMembershipTests(SurveyEventSetupMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.record_validation()
        call_command(
            "activate_survey_event",
            survey=self.survey.code,
            apply=True,
            stdout=StringIO(),
        )
        self.user = get_user_model().objects.create_user(username="dynamic_analyst")

    def test_membership_preview_does_not_write(self):
        call_command(
            "grant_survey_membership",
            survey=self.survey.code,
            username=self.user.username,
            role="analyst",
            stdout=StringIO(),
        )
        self.assertFalse(SurveyMembership.objects.filter(user=self.user).exists())

    def test_membership_apply_sets_analyst_capabilities(self):
        call_command(
            "grant_survey_membership",
            survey=self.survey.code,
            username=self.user.username,
            role="analyst",
            apply=True,
            stdout=StringIO(),
        )
        membership = SurveyMembership.objects.get(user=self.user, survey=self.survey)
        self.assertTrue(membership.can_monitor)
        self.assertTrue(membership.can_analyse)
        self.assertFalse(membership.can_export)
