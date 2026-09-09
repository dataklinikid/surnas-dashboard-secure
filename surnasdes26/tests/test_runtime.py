from django.test import TestCase, override_settings

from aggregate.models import SurveyAccess, SurveyDataSource, SurveyMetadataVersion
from surnasdes26.services.metadata import load_metadata
from surnasdes26.services.runtime import metadata_sha256, resolve_survey


@override_settings(SURVEY_CONTROL_PLANE_ENABLED=True)
class RuntimeSurveyResolverTests(TestCase):
    def setUp(self):
        load_metadata.cache_clear()
        self.survey = SurveyAccess.objects.get(code="surnasfeb26")

    def tearDown(self):
        load_metadata.cache_clear()

    def create_runtime_config(self, sha256=None):
        payload = {
            "metadata_schema_version": 1,
            "survey": {"code": "surnasfeb26"},
            "variables": {"Q_TEST": {"label": "Variabel runtime"}},
        }
        SurveyDataSource.objects.create(
            survey=self.survey,
            connection_alias="csweb_primary",
            environment_prefix="CSWEB_PRIMARY",
            database_name="dbcs_runtime_report",
            table_name="h0",
            identity_column="Q_AC",
            latest_id_column="H0_ID",
            target_n=100,
        )
        SurveyMetadataVersion.objects.create(
            survey=self.survey,
            version="metadata_v1",
            questionnaire_key="SURNASFEB26_RUNTIME_DICT",
            source_database="dbcs_runtime_report",
            payload=payload,
            sha256=sha256 or metadata_sha256(payload),
            is_active=True,
        )
        return payload

    def test_incomplete_control_plane_falls_back_to_json(self):
        manifest = resolve_survey("surnasfeb26")
        self.assertEqual(manifest["configuration_source"], "json")

    def test_complete_control_plane_uses_postgresql(self):
        self.create_runtime_config()
        manifest = resolve_survey("surnasfeb26")
        self.assertEqual(manifest["configuration_source"], "postgresql")
        self.assertEqual(manifest["database"]["name"], "dbcs_runtime_report")
        self.assertEqual(manifest["metadata"]["version"], "metadata_v1")

    def test_invalid_metadata_checksum_falls_back_to_json(self):
        self.create_runtime_config(sha256="0" * 64)
        manifest = resolve_survey("surnasfeb26")
        self.assertEqual(manifest["configuration_source"], "json")

    def test_metadata_loader_uses_active_postgresql_payload(self):
        payload = self.create_runtime_config()
        loaded = load_metadata("surnasfeb26")
        self.assertEqual(loaded["variables"], payload["variables"])
