import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from aggregate.models import SurveyAccess, SurveyMembership, SurveyMetadataVersion
from aggregate.metadata_onboarding import monitoring_dashboard_config
from aggregate.weighting import active_weight_status
from surnasdes26.services.dataset import DEMO_PATH, get_dataset
from surnasdes26.services.runtime import resolve_survey
from surnasdes26.services.runtime import metadata_sha256


@override_settings(SURVEY_CONTROL_PLANE_ENABLED=True)
class DynamicEventIntegrationTests(TestCase):
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
        survey = SurveyAccess.objects.get(code="simulasi_dinamis26")
        source_metadata = SurveyAccess.objects.get(
            code="surnasfeb26"
        ).metadata_versions.get(is_active=True)
        payload = {**source_metadata.payload, "survey": {**source_metadata.payload["survey"]}}
        payload["survey"].update(
            {
                "code": survey.code,
                "name": survey.name,
                "dictionary_name": "SIMULASI_DINAMIS26_DICT",
            }
        )
        SurveyMetadataVersion.objects.create(
            survey=survey,
            version="metadata_v1",
            questionnaire_key="SIMULASI_DINAMIS26_DICT",
            source_database="dbcs_simulasi_dinamis26_report",
            payload=payload,
            sha256=metadata_sha256(payload),
            source_name="simulasi_dinamis26_metadata.json",
            is_active=True,
        )
        survey.status = SurveyAccess.Status.VALIDATION
        survey.dashboard_config = monitoring_dashboard_config(payload)
        survey.save(update_fields=("status", "dashboard_config"))
        survey.event_modules.filter(module__code="weighted_analysis").update(enabled=False)
        metadata_variables = payload["variables"]
        validation_data = {name.upper(): [1, 1] for name in metadata_variables}
        validation_data.update({"Q_AC": [1, 2], "H0_ID": [10, 11]})
        with patch(
            "aggregate.management.commands.validate_survey_event.read_data_source"
        ) as reader:
            import pandas as pd

            reader.return_value = pd.DataFrame(validation_data)
            call_command(
                "validate_survey_event",
                survey=survey.code,
                apply=True,
                stdout=StringIO(),
            )
        self.user = get_user_model().objects.create_user(username="dynamic_viewer")
        SurveyMembership.objects.create(
            survey=survey,
            user=self.user,
            can_monitor=True,
            can_analyse=True,
        )
        call_command(
            "activate_survey_event",
            survey=survey.code,
            apply=True,
            stdout=StringIO(),
        )
        self.survey = SurveyAccess.objects.get(code="simulasi_dinamis26")

    def test_database_only_event_appears_for_member(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("aggregate:home"))
        self.assertContains(response, "Simulasi Dinamis 2026")
        self.assertContains(response, "/surveys/simulasi_dinamis26/analysis/")

    def test_database_only_event_analysis_is_unweighted(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("surveys:analysis", kwargs={"survey_code": self.survey.code})
        )
        self.assertEqual(response.status_code, 200)
        dataset = get_dataset(force_refresh=True, survey_code=self.survey.code)
        status = active_weight_status(dataset, self.survey.code)
        self.assertFalse(status["available"])

    @override_settings(SURNAS_DEMO_MODE=False)
    def test_database_check_uses_runtime_event_without_json(self):
        output = StringIO()
        environment = {
            "SURNAS_DB_USER": "readonly",
            "SURNAS_DB_PASSWORD": "test-secret",
        }
        with patch.dict(os.environ, environment), patch(
            "surnasdes26.management.commands.check_survey_db.count_h0",
            return_value=1263,
        ):
            call_command(
                "check_survey_db",
                survey=self.survey.code,
                stdout=output,
            )
        self.assertIn("Database reporting: OK", output.getvalue())
        self.assertIn("Survey code: simulasi_dinamis26", output.getvalue())
        self.assertEqual(resolve_survey(self.survey.code)["configuration_source"], "postgresql")
