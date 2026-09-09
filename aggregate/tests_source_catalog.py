from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from aggregate.models import (
    SurveyAccess,
    SurveyConnectionProfile,
    SurveyDataSource,
)
from aggregate.source_catalog import (
    SourceCatalogError,
    discover_reporting_databases,
    suggested_event_code,
    suggested_event_name,
    verified_link_candidate,
)
from surnasdes26.services.legacy_db import get_connection_profile_config


class FakeCursor:
    def __init__(self):
        self.result = []
        self.queries = []

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.queries.append((normalized, params))
        if normalized == "SHOW DATABASES":
            self.result = [
                ("information_schema",),
                ("cspro",),
                ("dbcs76_surnasfeb26_report",),
                ("dbcs81_surabaya27_report",),
            ]
        elif "information_schema.TABLES" in normalized:
            self.result = [
                ("dbcs76_surnasfeb26_report", "h0", 1263),
                ("dbcs76_surnasfeb26_report", "cspro_meta", 1),
                ("dbcs81_surabaya27_report", "h0", 1200),
                ("dbcs81_surabaya27_report", "cspro_meta", 1),
            ]
        elif "information_schema.COLUMNS" in normalized:
            self.result = [
                ("dbcs76_surnasfeb26_report", "h0", 418, 1, 1),
                ("dbcs81_surabaya27_report", "h0", 300, 1, 0),
            ]
        else:
            raise AssertionError(f"Query tidak diharapkan: {normalized}")

    def fetchall(self):
        return list(self.result)

    def fetchone(self):
        return self.result[0] if self.result else None

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.fake_cursor = FakeCursor()

    def cursor(self):
        return self.fake_cursor

    def close(self):
        pass


class SourceCatalogServiceTests(TestCase):
    def setUp(self):
        self.profile = SurveyConnectionProfile.objects.create(
            code="catalog_service",
            name="Catalog Service",
            environment_prefix="CATALOG_SERVICE_DB",
            discovery_environment_prefix="CATALOG_DISCOVERY_DB",
        )

    def test_discovery_filters_operational_databases_and_uses_metadata_only(self):
        connection = FakeConnection()
        with patch(
            "aggregate.source_catalog.get_connection_profile_config",
            return_value={"HOST": "127.0.0.1"},
        ), patch(
            "aggregate.source_catalog.connect_database_config",
            return_value=connection,
        ):
            rows = discover_reporting_databases(self.profile)
        self.assertEqual(
            [row["database_name"] for row in rows],
            ["dbcs76_surnasfeb26_report", "dbcs81_surabaya27_report"],
        )
        self.assertEqual(rows[0]["suggested_code"], "surnasfeb26")
        self.assertTrue(rows[0]["has_latest_id"])
        self.assertTrue(rows[0]["has_cspro_meta"])
        self.assertFalse(rows[1]["has_latest_id"])
        query_text = " ".join(sql for sql, _params in connection.fake_cursor.queries)
        self.assertNotIn("SELECT *", query_text.upper())
        self.assertNotIn("INSERT", query_text.upper())
        self.assertNotIn("UPDATE", query_text.upper())
        self.assertNotIn("DELETE", query_text.upper())
        self.assertEqual(len(connection.fake_cursor.queries), 3)

    def test_suggested_code_accepts_both_known_prefix_orders(self):
        self.assertEqual(suggested_event_code("dbcs76_kota_uji27_report"), "kota_uji27")
        self.assertEqual(suggested_event_code("csdb76_kota_uji27_report"), "kota_uji27")
        self.assertEqual(suggested_event_name("dbcs76_kota_uji27_report"), "Kota Uji 27")

    def test_link_candidate_is_reverified_and_rejects_missing_identity(self):
        with patch(
            "aggregate.source_catalog.discover_reporting_databases",
            return_value=[
                {
                    "database_name": "dbcs90_invalid_report",
                    "table_name": "h0",
                    "has_identity": False,
                    "has_cspro_meta": True,
                }
            ],
        ):
            with self.assertRaises(SourceCatalogError):
                verified_link_candidate(self.profile, "dbcs90_invalid_report")

    def test_link_candidate_rejects_database_without_production_metadata(self):
        with patch(
            "aggregate.source_catalog.discover_reporting_databases",
            return_value=[
                {
                    "database_name": "dbcs90_no_meta_report",
                    "table_name": "h0",
                    "has_identity": True,
                    "has_cspro_meta": False,
                }
            ],
        ):
            with self.assertRaisesMessage(SourceCatalogError, "cspro_meta"):
                verified_link_candidate(self.profile, "dbcs90_no_meta_report")

    def test_profile_discovery_credentials_are_separate_from_runtime(self):
        environment = {
            "CATALOG_DISCOVERY_DB_USER": "catalog_ro",
            "CATALOG_DISCOVERY_DB_PASSWORD": "test-password",
            "CATALOG_DISCOVERY_DB_HOST": "127.0.0.1",
            "CATALOG_DISCOVERY_DB_PORT": "3307",
        }
        with patch.dict("os.environ", environment, clear=False):
            config = get_connection_profile_config(self.profile)
        self.assertEqual(config["USER"], "catalog_ro")
        self.assertEqual(config["PORT"], 3307)
        self.assertEqual(config["NAME"], "")


class SourceCatalogUITests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="catalog_admin", password="test-password", is_staff=True
        )
        self.regular = get_user_model().objects.create_user(
            username="catalog_regular", password="test-password"
        )
        self.profile = SurveyConnectionProfile.objects.create(
            code="catalog_ui",
            name="CSWeb Utama",
            environment_prefix="CATALOG_UI_DB",
            discovery_environment_prefix="CATALOG_UI_DISCOVERY_DB",
        )
        linked_event = SurveyAccess.objects.create(
            code="surnasfeb26_catalog",
            name="Surnas Tertaut",
            status=SurveyAccess.Status.ACTIVE,
            active=True,
        )
        SurveyDataSource.objects.create(
            survey=linked_event,
            connection_profile=self.profile,
            connection_alias=self.profile.code,
            environment_prefix=self.profile.environment_prefix,
            database_name="dbcs76_surnasfeb26_report",
            table_name="h0",
        )
        self.rows = [
            {
                "database_name": "dbcs76_surnasfeb26_report",
                "table_name": "h0",
                "estimated_rows": 1263,
                "column_count": 418,
                "has_identity": True,
                "has_latest_id": True,
                "has_cspro_meta": True,
                "suggested_code": "surnasfeb26",
            },
            {
                "database_name": "dbcs81_surabaya27_report",
                "table_name": "h0",
                "estimated_rows": 1200,
                "column_count": 300,
                "has_identity": True,
                "has_latest_id": False,
                "has_cspro_meta": True,
                "suggested_code": "surabaya27",
            },
            {
                "database_name": "dbcs82_rusak_report",
                "table_name": "",
                "estimated_rows": None,
                "column_count": 0,
                "has_identity": False,
                "has_latest_id": False,
                "has_cspro_meta": False,
                "suggested_code": "rusak",
            },
        ]

    def url(self):
        return reverse("aggregate:source_catalog")

    def test_regular_user_cannot_scan_catalog(self):
        self.client.force_login(self.regular)
        self.assertEqual(self.client.get(self.url()).status_code, 302)

    def test_staff_catalog_marks_linked_available_and_invalid_without_writes(self):
        self.client.force_login(self.staff)
        event_count = SurveyAccess.objects.count()
        source_count = SurveyDataSource.objects.count()
        with patch("aggregate.views.discover_reporting_databases", return_value=self.rows):
            response = self.client.post(
                self.url(), {"connection_profile": self.profile.pk}
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sudah tertaut")
        self.assertContains(response, "Belum tertaut")
        self.assertContains(response, "Tabel h0 tidak ditemukan")
        self.assertContains(response, "Surnas Tertaut")
        self.assertContains(response, "Tautkan sebagai event")
        self.assertEqual(SurveyAccess.objects.count(), event_count)
        self.assertEqual(SurveyDataSource.objects.count(), source_count)

    def test_discovery_error_is_sanitized_for_staff(self):
        self.client.force_login(self.staff)
        with patch(
            "aggregate.views.discover_reporting_databases",
            side_effect=SourceCatalogError("Catalog tidak dapat dibaca."),
        ):
            response = self.client.post(
                self.url(), {"connection_profile": self.profile.pk}
            )
        self.assertContains(response, "Catalog tidak dapat dibaca")

    def test_available_source_link_seeds_verified_wizard_state(self):
        candidate = self.rows[1]
        self.client.force_login(self.staff)
        with patch("aggregate.views.verified_link_candidate", return_value=candidate):
            response = self.client.post(
                reverse("aggregate:source_catalog_link"),
                {
                    "connection_profile": self.profile.pk,
                    "database_name": candidate["database_name"],
                },
            )
        self.assertRedirects(response, reverse("aggregate:event_onboarding_identity"))
        state = self.client.session["event_onboarding_v2"]
        self.assertEqual(state["identity"]["code"], "surabaya27")
        self.assertEqual(
            state["data_source"]["database_name"],
            "dbcs81_surabaya27_report",
        )
        self.assertEqual(state["data_source"]["identity_column"], "Q_AC")
        self.assertEqual(state["data_source"]["latest_id_column"], "")

    def test_already_linked_source_cannot_seed_wizard(self):
        candidate = self.rows[0]
        self.client.force_login(self.staff)
        with patch("aggregate.views.verified_link_candidate", return_value=candidate):
            response = self.client.post(
                reverse("aggregate:source_catalog_link"),
                {
                    "connection_profile": self.profile.pk,
                    "database_name": candidate["database_name"],
                },
            )
        self.assertRedirects(response, self.url())
        self.assertNotIn("event_onboarding_v2", self.client.session)

    def test_regular_user_cannot_link_catalog_source(self):
        self.client.force_login(self.regular)
        response = self.client.post(
            reverse("aggregate:source_catalog_link"),
            {
                "connection_profile": self.profile.pk,
                "database_name": "dbcs81_surabaya27_report",
            },
        )
        self.assertEqual(response.status_code, 302)
