from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from aggregate.event_validation import event_configuration_signature
from aggregate.models import (
    EventModuleDefinition,
    EventType,
    Region,
    SurveyAccess,
    SurveyConnectionProfile,
    SurveyDataSource,
    SurveyEventModule,
    SurveyMembership,
    SurveyMetadataVersion,
    SurveyProgram,
)
from surnasdes26.services.runtime import metadata_sha256


class EventActivationUITests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="activation_admin", password="test-password", is_staff=True
        )
        self.regular = get_user_model().objects.create_user(
            username="activation_regular", password="test-password"
        )
        self.analyst = get_user_model().objects.create_user(
            username="activation_analyst", password="test-password"
        )
        program = SurveyProgram.objects.create(code="activation_program", name="Program")
        region = Region.objects.create(
            code="activation_region", name="Region", level=Region.Level.OTHER
        )
        profile = SurveyConnectionProfile.objects.create(
            code="activation_profile", name="Profile", environment_prefix="ACTIVATION_DB"
        )
        self.survey = SurveyAccess.objects.create(
            code="activation_target27",
            name="Activation Target 2027",
            event_type=EventType.objects.get(code="opinion_survey"),
            program=program,
            region=region,
            status=SurveyAccess.Status.VALIDATION,
            validation_state=SurveyAccess.ValidationState.PASSED,
            validated_at=timezone.now(),
            validation_fingerprint="d" * 64,
            dashboard_config={
                "monitoring_group_variable": "Q_B",
                "monitoring_group_label": "Distribusi uji",
            },
            active=False,
        )
        source = SurveyDataSource.objects.create(
            survey=self.survey,
            connection_profile=profile,
            connection_alias=profile.code,
            environment_prefix=profile.environment_prefix,
            database_name="dbcs_activation_report",
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
                "dictionary_name": "ACTIVATION_UI_DICT",
                "source_table": "h0",
                "aggregate_only": True,
            },
            "variables": {"Q_B": {"label": "Uji", "values": {"1": "Ya"}}},
            "multiple_answer_groups": {},
            "build_report": {"contains_respondent_rows": False},
        }
        metadata = SurveyMetadataVersion.objects.create(
            survey=self.survey,
            version="metadata_v1",
            questionnaire_key="ACTIVATION_UI_DICT",
            source_database="dbcs_activation_report",
            payload=payload,
            sha256=metadata_sha256(payload),
            is_active=True,
        )
        for code in ("fieldwork_monitoring", "survey_analytics"):
            SurveyEventModule.objects.create(
                survey=self.survey,
                module=EventModuleDefinition.objects.get(code=code),
                readiness=SurveyEventModule.Readiness.READY,
            )
        signature = event_configuration_signature(self.survey, source, metadata)
        self.survey.validation_report = {
            "final_rows": 2,
            "dataset_fingerprint": "d" * 64,
            "configuration_signature": signature,
            "errors": [],
        }
        self.survey.save(update_fields=("validation_report",))

    def url(self):
        return reverse("aggregate:event_activation_review", args=(self.survey.code,))

    def add_membership(self, role="analyst"):
        self.client.force_login(self.staff)
        return self.client.post(
            self.url(),
            {
                "action": "save_membership",
                "membership-user": self.analyst.pk,
                "membership-role": role,
            },
        )

    def test_regular_user_cannot_open_activation_review(self):
        self.client.force_login(self.regular)
        self.assertEqual(self.client.get(self.url()).status_code, 302)

    def test_gate_blocks_activation_without_operational_user(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url())
        self.assertContains(response, "Minimal satu pengguna operasional")
        self.assertNotContains(response, "Aktifkan event")

    def test_membership_form_creates_analyst_capabilities(self):
        response = self.add_membership()
        self.assertRedirects(response, self.url())
        membership = SurveyMembership.objects.get(survey=self.survey, user=self.analyst)
        self.assertTrue(membership.can_monitor)
        self.assertTrue(membership.can_analyse)
        self.assertFalse(membership.can_export)
        response = self.client.get(self.url())
        self.assertContains(response, "Siap diaktifkan")

    def test_removing_last_membership_blocks_gate_again(self):
        self.add_membership()
        membership = SurveyMembership.objects.get(survey=self.survey, user=self.analyst)
        response = self.client.post(
            self.url(),
            {"action": "remove_membership", "membership_id": membership.pk},
        )
        self.assertRedirects(response, self.url())
        self.assertFalse(SurveyMembership.objects.filter(pk=membership.pk).exists())

    def test_wrong_confirmation_does_not_activate(self):
        self.add_membership()
        response = self.client.post(
            self.url(),
            {
                "action": "activate",
                "activation-confirmation_code": "wrong_code",
                "activation-confirm": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kode konfirmasi tidak sama")
        self.survey.refresh_from_db()
        self.assertFalse(self.survey.active)

    def test_confirmed_activation_changes_status_once(self):
        self.add_membership(role="admin")
        response = self.client.post(
            self.url(),
            {
                "action": "activate",
                "activation-confirmation_code": self.survey.code,
                "activation-confirm": "on",
            },
        )
        self.assertRedirects(response, reverse("aggregate:home"))
        self.survey.refresh_from_db()
        self.assertTrue(self.survey.active)
        self.assertEqual(self.survey.status, SurveyAccess.Status.ACTIVE)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
