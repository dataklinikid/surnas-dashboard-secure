import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from aggregate.models import (
    Region,
    SurveyAccess,
    SurveyDataSource,
    SurveyMetadataVersion,
    SurveyProgram,
)


COMMAND_ARGUMENTS = {
    "survey": "surnasfeb26",
    "program_code": "surnas",
    "program_name": "Survei Nasional",
    "region_code": "indonesia",
    "region_name": "Indonesia",
    "region_level": "national",
    "metadata_version": "metadata_v1",
}


class SyncSurveyEventConfigTests(TestCase):
    def run_command(self, apply=False):
        output = StringIO()
        arguments = dict(COMMAND_ARGUMENTS)
        if apply:
            arguments["apply"] = True
        with patch.dict(os.environ, {"SURNAS_DB_NAME": "dbcs_surnasfeb26_report"}):
            call_command("sync_survey_event_config", stdout=output, **arguments)
        return output.getvalue()

    def test_preview_does_not_change_control_plane(self):
        output = self.run_command()
        self.assertIn("PREVIEW", output)
        self.assertFalse(SurveyProgram.objects.filter(code="surnas").exists())
        self.assertFalse(Region.objects.filter(code="indonesia").exists())
        self.assertFalse(SurveyDataSource.objects.exists())
        self.assertFalse(SurveyMetadataVersion.objects.exists())

    def test_apply_enriches_existing_survey(self):
        original = SurveyAccess.objects.get(code="surnasfeb26")
        output = self.run_command(apply=True)
        survey = SurveyAccess.objects.get(code="surnasfeb26")
        self.assertEqual(survey.pk, original.pk)
        self.assertEqual(survey.program.code, "surnas")
        self.assertEqual(survey.region.code, "indonesia")
        self.assertEqual(survey.data_source.database_name, "dbcs_surnasfeb26_report")
        self.assertEqual(
            survey.data_source.connection_profile.code,
            survey.data_source.connection_alias,
        )
        self.assertIn("APPLIED", output)

    def test_apply_stores_metadata_version_and_sha256(self):
        self.run_command(apply=True)
        metadata = SurveyMetadataVersion.objects.get(
            survey__code="surnasfeb26",
            version="metadata_v1",
        )
        self.assertTrue(metadata.is_active)
        self.assertEqual(len(metadata.sha256), 64)
        self.assertIsInstance(metadata.payload["variables"], dict)

    def test_apply_is_idempotent(self):
        self.run_command(apply=True)
        self.run_command(apply=True)
        self.assertEqual(SurveyProgram.objects.filter(code="surnas").count(), 1)
        self.assertEqual(Region.objects.filter(code="indonesia").count(), 1)
        self.assertEqual(SurveyDataSource.objects.filter(survey__code="surnasfeb26").count(), 1)
        self.assertEqual(SurveyMetadataVersion.objects.filter(survey__code="surnasfeb26").count(), 1)

    def test_database_credentials_are_not_model_fields(self):
        self.run_command(apply=True)
        field_names = {field.name for field in SurveyDataSource._meta.fields}
        self.assertNotIn("username", field_names)
        self.assertNotIn("password", field_names)
