import json
import os
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from aggregate.metadata_onboarding import (
    inspect_metadata_source,
    prepare_metadata_candidate,
    reporting_column_names,
)
from aggregate.models import (
    SurveyAccess,
    SurveyDataSource,
    SurveyMetadataVersion,
)


class MetadataOnboardingTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="metadata_admin",
            password="test-password",
            is_staff=True,
        )
        self.regular = get_user_model().objects.create_user(
            username="metadata_regular",
            password="test-password",
        )
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
        template = SurveyAccess.objects.get(code="surnasfeb26")
        self.survey = SurveyAccess.objects.create(
            code="metadata_uji27",
            name="Metadata Uji 2027",
            event_type=template.event_type,
            program=template.program,
            region=template.region,
            status=SurveyAccess.Status.DRAFT,
            active=False,
        )
        source = template.data_source
        SurveyDataSource.objects.create(
            survey=self.survey,
            connection_profile=source.connection_profile,
            engine=source.engine,
            connection_alias=source.connection_alias,
            environment_prefix=source.environment_prefix,
            database_name="dbcs_metadata_uji27_report",
            table_name="h0",
            identity_column="Q_AC",
            latest_id_column="H0_ID",
            target_n=1260,
        )
        self.template = template
        self.report = {
            "checked_at": "2027-01-01T00:00:00+00:00",
            "survey_code": self.survey.code,
            "connection_profile": source.connection_profile.code,
            "environment_prefix": source.environment_prefix,
            "database_name": "dbcs_metadata_uji27_report",
            "table_name": "h0",
            "raw_rows": 1260,
            "target_n": 1260,
            "available_column_count": 418,
            "metadata_column_count": 315,
            "required_column_count": 317,
            "missing_column_count": 0,
            "missing_columns": [],
            "errors": [],
            "warnings": [],
            "passed": True,
            "read_only_queries": 3,
        }

    def metadata_url(self):
        return reverse("aggregate:event_metadata_setup", args=(self.survey.code,))

    def test_reporting_columns_include_free_text_and_technical_fields(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"COLUMN_NAME": "H0-ID"},
            {"COLUMN_NAME": "Q_NM"},
            {"COLUMN_NAME": "WAKTU"},
            {"COLUMN_NAME": "Q_D"},
        ]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        driver = SimpleNamespace(cursors=SimpleNamespace(DictCursor=object()))
        with patch(
            "aggregate.metadata_onboarding.get_data_source_config",
            return_value={"NAME": "dbcs_metadata_uji27_report", "TABLE": "h0"},
        ), patch(
            "aggregate.metadata_onboarding._mysql_driver",
            return_value=driver,
        ), patch(
            "aggregate.metadata_onboarding.connect_database_config",
            return_value=connection,
        ):
            columns = reporting_column_names(self.survey)

        self.assertEqual(columns, ("H0_ID", "Q_NM", "WAKTU", "Q_D"))
        sql, params = cursor.execute.call_args.args
        self.assertIn("information_schema.COLUMNS", sql)
        self.assertEqual(params, ("dbcs_metadata_uji27_report", "h0"))

    def database_metadata(self, *, dictionary_name="METADATA_UJI27_DICT"):
        payload = json.loads(
            json.dumps(self.template.metadata_versions.get(is_active=True).payload)
        )
        payload["survey"].update(
            {
                "code": self.survey.code,
                "name": self.survey.name,
                "dictionary_name": dictionary_name,
                "source_table": "h0",
            }
        )
        return payload

    def database_candidate(self, *, payload=None, report=None):
        signature = {
            "kind": "database_cspro_meta",
            "row_id": 1,
            "cspro_version": "CSPro 7.7",
            "dictionary_sha256": "a" * 64,
            "contains_respondent_rows": False,
        }
        return payload or self.database_metadata(), report or self.report, signature

    def test_regular_user_cannot_open_metadata_setup(self):
        self.client.force_login(self.regular)
        response = self.client.get(self.metadata_url())
        self.assertEqual(response.status_code, 302)

    def test_staff_home_lists_draft_but_regular_home_does_not(self):
        self.client.force_login(self.staff)
        staff_home = self.client.get(reverse("aggregate:home"))
        self.assertContains(staff_home, self.survey.name)
        self.assertContains(staff_home, "Metadata & koneksi")

        self.client.force_login(self.regular)
        regular_home = self.client.get(reverse("aggregate:home"))
        self.assertNotContains(regular_home, self.survey.name)

    def test_event_specific_metadata_is_saved_after_check(self):
        self.client.force_login(self.staff)
        with patch(
            "aggregate.metadata_onboarding._database_metadata_candidate",
            return_value=self.database_candidate(),
        ):
            response = self.client.post(
                self.metadata_url(),
                {
                    "version": "metadata_v1",
                },
            )
        self.assertRedirects(response, self.metadata_url())
        metadata = SurveyMetadataVersion.objects.get(survey=self.survey)
        self.assertEqual(metadata.payload["survey"]["code"], self.survey.code)
        self.assertEqual(metadata.payload["survey"]["name"], self.survey.name)
        self.assertEqual(metadata.questionnaire_key, "METADATA_UJI27_DICT")
        self.assertEqual(metadata.source_database, "dbcs_metadata_uji27_report")
        self.assertEqual(metadata.onboarding_report["read_only_queries"], 3)
        self.assertNotIn("password", metadata.onboarding_report)
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.status, SurveyAccess.Status.VALIDATION)
        self.assertFalse(self.survey.active)
        self.assertEqual(
            self.survey.dashboard_config["monitoring_group_variable"],
            "Q_F",
        )
        self.assertEqual(
            self.survey.dashboard_config["monitoring_group_label"],
            "Q_F. PROVINSI",
        )

    def test_failed_schema_check_does_not_store_metadata(self):
        self.client.force_login(self.staff)
        failed = {
            **self.report,
            "missing_column_count": 1,
            "missing_columns": ["Q_MISSING"],
            "errors": ["1 kolom wajib tidak tersedia pada tabel reporting."],
            "passed": False,
        }
        with patch(
            "aggregate.metadata_onboarding._database_metadata_candidate",
            return_value=self.database_candidate(report=failed),
        ):
            response = self.client.post(
                self.metadata_url(),
                {
                    "version": "metadata_v1",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "metadata belum disimpan")
        self.assertFalse(self.survey.metadata_versions.exists())
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.status, SurveyAccess.Status.DRAFT)

    def test_upload_with_wrong_event_code_is_rejected(self):
        self.client.force_login(self.staff)
        payload = self.database_metadata()
        payload["survey"] = {**payload["survey"], "code": "event_lain"}
        with patch(
            "aggregate.metadata_onboarding._database_metadata_candidate",
            return_value=self.database_candidate(payload=payload),
        ):
            response = self.client.post(
                self.metadata_url(),
                {"version": "metadata_v1"},
            )
        self.assertContains(response, "Kode event pada metadata tidak cocok")
        self.assertFalse(self.survey.metadata_versions.exists())

    def test_metadata_from_another_event_cannot_be_reused(self):
        self.client.force_login(self.staff)
        payload = self.database_metadata(
            dictionary_name="SURVEI_NASIONAL_PDAT_FEB26_DICT"
        )
        with patch(
            "aggregate.metadata_onboarding._database_metadata_candidate",
            return_value=self.database_candidate(payload=payload),
        ):
            response = self.client.post(
                self.metadata_url(),
                {"version": "metadata_v1"},
            )
        self.assertContains(response, "Identitas kuesioner sudah digunakan oleh event lain")
        self.assertFalse(self.survey.metadata_versions.exists())

    def test_metadata_page_has_no_template_event_option(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.metadata_url())
        self.assertNotContains(response, "Gunakan metadata dari event lain")
        self.assertNotContains(response, "Template event")
        self.assertNotContains(response, 'type="file"')
        self.assertContains(response, "Ambil dari database")

    def test_inspector_executes_only_two_select_queries(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (1260,)
        cursor.description = [("Q_AC",), ("H0_ID",), ("Q_B",)]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        payload = {
            "survey": {
                "code": self.survey.code,
                "source_table": "h0",
                "aggregate_only": True,
            },
            "variables": {"Q_B": {"label": "Uji", "values": {"1": "Ya"}}},
            "multiple_answer_groups": {},
            "build_report": {"contains_respondent_rows": False},
        }
        with patch(
            "aggregate.metadata_onboarding.get_data_source_config",
            return_value={"TABLE": "h0"},
        ), patch(
            "aggregate.metadata_onboarding.connect_database_config",
            return_value=connection,
        ):
            report = inspect_metadata_source(survey=self.survey, payload=payload)

        queries = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertEqual(queries, ["SELECT COUNT(*) FROM `h0`", "SELECT * FROM `h0` LIMIT 0"])
        self.assertTrue(report["passed"])
        self.assertEqual(report["read_only_queries"], 2)

    def test_database_metadata_is_built_from_cspro_meta_with_three_selects(self):
        dictionary = """[Dictionary]
Name=METADATA_UJI27_PRODUCTION
Label=Metadata Uji Produksi
Version=7.7
[Record]
Label=Demografi
[Item]
Name=Q_B
Label=Jenis kelamin
DataType=Numeric
[ValueSet]
Value=1;Laki-laki
Value=2;Perempuan
"""

        class Cursor:
            def __init__(self):
                self.queries = []
                self.mode = ""

            def execute(self, sql, params=None):
                self.queries.append((" ".join(sql.split()), params))
                if "FROM cspro_meta" in sql:
                    self.mode = "metadata"
                elif "information_schema.COLUMNS" in sql:
                    self.mode = "columns"
                elif "COUNT(*)" in sql:
                    self.mode = "count"

            def fetchone(self):
                if self.mode == "metadata":
                    return {
                        "id": 1,
                        "cspro_version": "CSPro 7.7",
                        "dictionary": dictionary,
                        "source_modified_time": "2026-09-09 07:32:42",
                        "created_time": "2026-09-09 07:32:42",
                        "modified_time": "2026-09-09 07:32:42",
                    }
                if self.mode == "count":
                    return {"raw_rows": 4}
                return None

            def fetchall(self):
                return [
                    {"COLUMN_NAME": "Q_AC"},
                    {"COLUMN_NAME": "H0-ID"},
                    {"COLUMN_NAME": "Q_B"},
                ]

            def close(self):
                pass

        cursor = Cursor()
        connection = MagicMock()
        connection.cursor.return_value = cursor
        driver = SimpleNamespace(cursors=SimpleNamespace(DictCursor=object()))
        with patch(
            "aggregate.metadata_onboarding.get_data_source_config",
            return_value={
                "NAME": "dbcs_metadata_uji27_report",
                "TABLE": "h0",
            },
        ), patch(
            "aggregate.metadata_onboarding._mysql_driver",
            return_value=driver,
        ), patch(
            "aggregate.metadata_onboarding.connect_database_config",
            return_value=connection,
        ):
            candidate = prepare_metadata_candidate(survey=self.survey)

        self.assertEqual(candidate["questionnaire_key"], "METADATA_UJI27_PRODUCTION")
        self.assertEqual(candidate["source_database"], "dbcs_metadata_uji27_report")
        self.assertEqual(candidate["onboarding_report"]["raw_rows"], 4)
        self.assertEqual(candidate["onboarding_report"]["read_only_queries"], 3)
        self.assertEqual(len(cursor.queries), 3)
        self.assertTrue(all(query.startswith("SELECT") for query, _params in cursor.queries))
