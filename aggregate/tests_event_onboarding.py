from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from aggregate.forms import EventDataSourceForm
from aggregate.models import (
    EventModuleDefinition,
    EventType,
    Region,
    SurveyAccess,
    SurveyConnectionProfile,
    SurveyEventModule,
    SurveyProgram,
)


class EventOnboardingTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="event_admin",
            password="test-password",
            is_staff=True,
        )
        self.regular = get_user_model().objects.create_user(
            username="regular_analyst",
            password="test-password",
        )
        self.program = SurveyProgram.objects.create(
            code="pilkada_event",
            name="Program Pilkada",
        )
        self.region = Region.objects.create(
            code="kota_uji",
            name="Kota Uji",
            level=Region.Level.REGENCY,
        )
        self.profile = SurveyConnectionProfile.objects.create(
            code="csweb_test",
            name="CSWeb Test",
            environment_prefix="CSWEB_TEST",
            discovery_environment_prefix="CSWEB_CATALOG_TEST",
        )
        self.identity = {
            "code": "pilkada_uji27",
            "name": "Survei Pilkada Uji 2027",
            "event_type": EventType.objects.get(code="opinion_survey").pk,
            "period_start": "2027-01-01",
            "period_end": "2027-01-31",
        }
        self.existing_references = {
            "program_existing": self.program.pk,
            "region_existing": self.region.pk,
        }
        self.source = {
            "connection_profile": self.profile.pk,
            "database_name": "dbcs_pilkada_uji27_report",
            "table_name": "h0",
            "identity_column": "Q_AC",
            "latest_id_column": "H0_ID",
            "valid_column": "",
            "valid_value": "",
            "target_n": 800,
        }

    def advance_to_review(self, references=None):
        self.client.post(reverse("aggregate:event_onboarding_identity"), self.identity)
        self.client.post(
            reverse("aggregate:event_onboarding_references"),
            references or self.existing_references,
        )
        module_ids = list(
            EventModuleDefinition.objects.filter(
                code__in=("fieldwork_monitoring", "survey_analytics")
            ).values_list("pk", flat=True)
        )
        self.client.post(
            reverse("aggregate:event_onboarding_modules"),
            {"modules": module_ids},
        )
        self.client.post(reverse("aggregate:event_onboarding_source"), self.source)

    def test_anonymous_user_cannot_open_wizard(self):
        response = self.client.get(reverse("aggregate:event_onboarding_identity"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_regular_user_cannot_open_wizard_or_see_menu(self):
        self.client.force_login(self.regular)
        response = self.client.get(reverse("aggregate:event_onboarding_identity"))
        self.assertEqual(response.status_code, 302)
        home = self.client.get(reverse("aggregate:home"))
        self.assertNotContains(home, "Buat event baru")

    def test_staff_sees_wizard_menu(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("aggregate:home"))
        self.assertContains(response, "Catalog sumber CSWeb")
        self.assertContains(response, "Buat event manual")

    def test_invalid_period_does_not_advance(self):
        self.client.force_login(self.staff)
        values = {**self.identity, "period_end": "2026-12-31"}
        response = self.client.post(reverse("aggregate:event_onboarding_identity"), values)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tanggal selesai tidak boleh lebih awal")

    def test_source_form_never_contains_credentials(self):
        field_names = set(EventDataSourceForm().fields)
        self.assertNotIn("host", field_names)
        self.assertNotIn("username", field_names)
        self.assertNotIn("password", field_names)

    def test_source_filter_requires_column_and_value_together(self):
        form = EventDataSourceForm({**self.source, "valid_column": "STATUS", "valid_value": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("harus diisi bersama-sama", str(form.non_field_errors()))

    def test_catalog_locked_source_ignores_posted_database_tampering(self):
        locked = {
            "connection_profile": self.profile.pk,
            "database_name": "dbcs76_catalog_uji27_report",
            "table_name": "h0",
            "identity_column": "Q_AC",
            "latest_id_column": "H0_ID",
            "valid_column": "",
            "valid_value": "",
            "target_n": None,
        }
        tampered = {
            **locked,
            "database_name": "dbcs76_database_lain_report",
            "table_name": "h9",
            "identity_column": "BAD_KEY",
        }
        form = EventDataSourceForm(
            tampered,
            initial=locked,
            locked_source={
                "connection_profile": self.profile.pk,
                "database_name": locked["database_name"],
                "table_name": "h0",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["database_name"], locked["database_name"])
        self.assertEqual(form.cleaned_data["table_name"], "h0")
        self.assertEqual(form.cleaned_data["identity_column"], "Q_AC")

    def test_review_does_not_create_any_new_record(self):
        self.client.force_login(self.staff)
        references = {
            "program_existing": "",
            "program_code": "program_baru27",
            "program_name": "Program Baru 2027",
            "region_existing": "",
            "region_code": "kabupaten_baru27",
            "region_name": "Kabupaten Baru",
            "region_level": Region.Level.REGENCY,
            "region_parent": "",
        }
        self.advance_to_review(references)
        response = self.client.get(reverse("aggregate:event_onboarding_review"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.identity["name"])
        self.assertFalse(SurveyAccess.objects.filter(code=self.identity["code"]).exists())
        self.assertFalse(SurveyProgram.objects.filter(code="program_baru27").exists())
        self.assertFalse(Region.objects.filter(code="kabupaten_baru27").exists())

    def test_confirmation_creates_complete_inactive_draft(self):
        self.client.force_login(self.staff)
        self.advance_to_review()
        response = self.client.post(reverse("aggregate:event_onboarding_review"))

        survey = SurveyAccess.objects.get(code=self.identity["code"])
        self.assertRedirects(
            response,
            reverse("aggregate:event_onboarding_done", args=(survey.code,)),
        )
        self.assertFalse(survey.active)
        self.assertEqual(survey.status, SurveyAccess.Status.DRAFT)
        self.assertEqual(survey.validation_state, SurveyAccess.ValidationState.NOT_RUN)
        self.assertEqual(survey.data_source.connection_profile, self.profile)
        self.assertEqual(survey.data_source.connection_alias, self.profile.code)
        self.assertEqual(survey.data_source.environment_prefix, "CSWEB_TEST")
        self.assertEqual(survey.data_source.database_name, self.source["database_name"])
        self.assertEqual(survey.metadata_versions.count(), 0)
        self.assertEqual(survey.memberships.count(), 0)
        self.assertEqual(survey.weight_sets.count(), 0)
        assignments = SurveyEventModule.objects.filter(survey=survey)
        self.assertFalse(
            assignments.exclude(readiness=SurveyEventModule.Readiness.PENDING).exists()
        )

    def test_catalog_draft_uses_discovery_prefix_without_changing_manual_runtime(self):
        self.client.force_login(self.staff)
        session = self.client.session
        session["event_onboarding_v2"] = {
            "catalog_source": {
                "connection_profile": self.profile.pk,
                "database_name": self.source["database_name"],
                "table_name": "h0",
            },
            "data_source": dict(self.source),
        }
        session.save()
        self.advance_to_review()
        self.client.post(reverse("aggregate:event_onboarding_review"))
        survey = SurveyAccess.objects.get(code=self.identity["code"])
        self.assertEqual(
            survey.data_source.environment_prefix,
            "CSWEB_CATALOG_TEST",
        )

    def test_confirmation_creates_new_program_and_region_atomically(self):
        self.client.force_login(self.staff)
        references = {
            "program_existing": "",
            "program_code": "program_baru27",
            "program_name": "Program Baru 2027",
            "region_existing": "",
            "region_code": "kabupaten_baru27",
            "region_name": "Kabupaten Baru",
            "region_level": Region.Level.REGENCY,
            "region_parent": self.region.pk,
        }
        self.advance_to_review(references)
        self.client.post(reverse("aggregate:event_onboarding_review"))

        survey = SurveyAccess.objects.get(code=self.identity["code"])
        self.assertEqual(survey.program.code, "program_baru27")
        self.assertEqual(survey.region.code, "kabupaten_baru27")
        self.assertEqual(survey.region.parent, self.region)

    def test_cancel_clears_session_without_creating_event(self):
        self.client.force_login(self.staff)
        self.client.post(reverse("aggregate:event_onboarding_identity"), self.identity)
        self.client.post(reverse("aggregate:event_onboarding_cancel"))
        self.assertFalse(SurveyAccess.objects.filter(code=self.identity["code"]).exists())
        response = self.client.get(reverse("aggregate:event_onboarding_source"))
        self.assertRedirects(response, reverse("aggregate:event_onboarding_identity"))
