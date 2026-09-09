from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class EventMetadataIsolationMigrationTests(TransactionTestCase):
    migrate_from = [("aggregate", "0012_profile_discovery_environment")]
    migrate_to = [("aggregate", "0013_event_metadata_isolation")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        SurveyAccess = old_apps.get_model("aggregate", "SurveyAccess")
        SurveyConnectionProfile = old_apps.get_model(
            "aggregate", "SurveyConnectionProfile"
        )
        SurveyDataSource = old_apps.get_model("aggregate", "SurveyDataSource")
        SurveyMetadataVersion = old_apps.get_model(
            "aggregate", "SurveyMetadataVersion"
        )

        profile, _ = SurveyConnectionProfile.objects.update_or_create(
            code="migration_csweb",
            defaults={
                "name": "Migration CSWeb",
                "environment_prefix": "MIGRATION_DB",
            },
        )
        canonical, _ = SurveyAccess.objects.update_or_create(
            code="surnasfeb26",
            defaults={
                "name": "Surnas Februari 2026",
                "status": "active",
                "active": True,
            },
        )
        template_copy, _ = SurveyAccess.objects.update_or_create(
            code="onboarding_sumber_uji27",
            defaults={
                "name": "Onboarding Sumber Uji 2027",
                "status": "active",
                "active": True,
            },
        )
        SurveyMetadataVersion.objects.filter(
            survey_id__in=(canonical.pk, template_copy.pk)
        ).delete()
        SurveyDataSource.objects.filter(
            survey_id__in=(canonical.pk, template_copy.pk)
        ).delete()
        SurveyDataSource.objects.create(
            survey=canonical,
            connection_profile=profile,
            connection_alias="migration_csweb",
            environment_prefix="MIGRATION_DB",
            database_name="dbcs76_surnasfeb26_report",
        )
        SurveyDataSource.objects.create(
            survey=template_copy,
            connection_profile=profile,
            connection_alias="migration_csweb",
            environment_prefix="MIGRATION_DB",
            database_name="dbcs81_onboarding_uji27_report",
        )

        def payload(code):
            return {
                "survey": {
                    "code": code,
                    "dictionary_name": "SURVEI_NASIONAL_PDAT_FEB26_DICT",
                    "source_table": "h0",
                    "aggregate_only": True,
                },
                "variables": {"Q_B": {"label": "Uji"}},
                "build_report": {"contains_respondent_rows": False},
            }

        SurveyMetadataVersion.objects.create(
            survey=canonical,
            version="metadata_v1",
            payload=payload(canonical.code),
            sha256="a" * 64,
            source_name="metadata.json",
            is_active=True,
        )
        SurveyMetadataVersion.objects.create(
            survey=template_copy,
            version="metadata_v1",
            payload=payload(template_copy.code),
            sha256="b" * 64,
            source_name="template:surnasfeb26:metadata_v1",
            is_active=True,
        )

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        self.apps = executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_template_lineage_is_deactivated_and_canonical_event_is_preserved(self):
        SurveyAccess = self.apps.get_model("aggregate", "SurveyAccess")
        SurveyMetadataVersion = self.apps.get_model(
            "aggregate", "SurveyMetadataVersion"
        )

        canonical = SurveyAccess.objects.get(code="surnasfeb26")
        template_copy = SurveyAccess.objects.get(code="onboarding_sumber_uji27")

        self.assertTrue(canonical.active)
        self.assertEqual(canonical.status, "active")
        self.assertTrue(
            SurveyMetadataVersion.objects.get(survey=canonical).is_active
        )
        self.assertFalse(template_copy.active)
        self.assertEqual(template_copy.status, "draft")
        self.assertFalse(
            SurveyMetadataVersion.objects.get(survey=template_copy).is_active
        )
