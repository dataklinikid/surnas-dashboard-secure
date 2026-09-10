from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from aggregate.models import (
    EventModuleDefinition,
    EventType,
    Region,
    SurveyAccess,
    SurveyDataSource,
    SurveyEventModule,
    SurveyMembership,
    SurveyMetadataVersion,
    SurveyProgram,
)


class AggregateAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="analyst", password="secure-test-password")

    def test_home_requires_login(self):
        response = self.client.get(reverse("aggregate:home"))
        self.assertEqual(response.status_code, 302)

    def test_survey_visible_after_permission(self):
        permission = Permission.objects.get(codename="access_surnasdes26_analysis")
        self.user.user_permissions.add(permission)
        self.client.force_login(self.user)
        response = self.client.get(reverse("aggregate:home"))
        self.assertContains(response, "Survei Nasional PDAT Februari 2026")
        self.assertContains(response, "/surveys/surnasfeb26/analysis/")

    def test_membership_controls_dynamic_survey_access(self):
        survey = SurveyAccess.objects.get(code="surnasfeb26")
        SurveyMembership.objects.create(
            user=self.user,
            survey=survey,
            can_monitor=True,
            can_analyse=False,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("aggregate:home"))

        self.assertContains(response, "/surveys/surnasfeb26/monitoring/")
        self.assertNotContains(response, "/surveys/surnasfeb26/analysis/")


class DynamicSurveyFoundationTests(TestCase):
    def setUp(self):
        self.program = SurveyProgram.objects.create(code="pilkada", name="Survei Pilkada")
        self.region = Region.objects.create(
            code="kota_surabaya",
            name="Kota Surabaya",
            level=Region.Level.REGENCY,
        )
        self.survey = SurveyAccess.objects.create(
            code="surabaya26",
            name="Survei Kota Surabaya 2026",
            program=self.program,
            region=self.region,
            status=SurveyAccess.Status.DRAFT,
            active=False,
        )

    def test_event_catalog_is_seeded(self):
        self.assertTrue(EventType.objects.filter(code="opinion_survey").exists())
        self.assertEqual(EventModuleDefinition.objects.filter(active=True).count(), 7)

    def test_event_modules_are_unique_per_event(self):
        module = EventModuleDefinition.objects.get(code="survey_analytics")
        SurveyEventModule.objects.create(survey=self.survey, module=module)
        with self.assertRaises(Exception):
            SurveyEventModule.objects.create(survey=self.survey, module=module)

    def test_survey_event_keeps_program_and_region(self):
        self.assertEqual(self.survey.program, self.program)
        self.assertEqual(self.survey.region, self.region)
        self.assertEqual(self.survey.status, SurveyAccess.Status.DRAFT)

    def test_data_source_stores_alias_without_credentials(self):
        source = SurveyDataSource.objects.create(
            survey=self.survey,
            connection_alias="csweb_primary",
            environment_prefix="CSWEB_PRIMARY",
            database_name="dbcs_surabaya26_report",
            table_name="h0",
            identity_column="Q_AC",
            latest_id_column="H0_ID",
            target_n=800,
        )
        self.assertEqual(source.survey, self.survey)
        self.assertFalse(hasattr(source, "password"))

    def test_metadata_versions_are_unique_per_survey(self):
        values = {
            "survey": self.survey,
            "version": "metadata_v1",
            "questionnaire_key": "SURABAYA26_DICT",
            "source_database": "dbcs_surabaya26_report",
            "payload": {"metadata_schema_version": 1, "variables": {}},
            "sha256": "a" * 64,
        }
        SurveyMetadataVersion.objects.create(**values)
        with self.assertRaises(Exception):
            SurveyMetadataVersion.objects.create(**values)

    def test_existing_survey_fields_remain_optional(self):
        legacy = SurveyAccess.objects.create(code="legacy26", name="Survei Lama")
        self.assertIsNone(legacy.program)
        self.assertIsNone(legacy.region)
        self.assertEqual(legacy.status, SurveyAccess.Status.ACTIVE)
