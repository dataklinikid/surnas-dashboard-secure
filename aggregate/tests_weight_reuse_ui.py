from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
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
    SurveyMetadataVersion,
    SurveyMembership,
    SurveyProgram,
    SurveyWeight,
    SurveyWeightSet,
)
from surnasdes26.services.runtime import metadata_sha256


class WeightReuseUITests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user(
            username="weight_admin", password="test-password", is_staff=True
        )
        self.regular = get_user_model().objects.create_user(
            username="weight_regular", password="test-password"
        )
        program = SurveyProgram.objects.create(code="weight_program", name="Weight Program")
        region = Region.objects.create(
            code="weight_region", name="Weight Region", level=Region.Level.OTHER
        )
        profile = SurveyConnectionProfile.objects.create(
            code="weight_profile",
            name="Weight Profile",
            environment_prefix="WEIGHT_DB",
        )
        self.target = SurveyAccess.objects.create(
            code="weight_target27",
            name="Weight Target 2027",
            event_type=EventType.objects.get(code="opinion_survey"),
            program=program,
            region=region,
            status=SurveyAccess.Status.VALIDATION,
            validation_state=SurveyAccess.ValidationState.PASSED,
            validated_at=timezone.now(),
            validation_fingerprint="a" * 64,
            dashboard_config={
                "monitoring_group_variable": "Q_B",
                "monitoring_group_label": "Distribusi uji",
            },
            active=False,
        )
        source = SurveyDataSource.objects.create(
            survey=self.target,
            connection_profile=profile,
            connection_alias=profile.code,
            environment_prefix=profile.environment_prefix,
            database_name="dbcs_weight_report",
            table_name="h0",
            identity_column="Q_AC",
            latest_id_column="H0_ID",
            target_n=2,
        )
        payload = {
            "metadata_schema_version": 1,
            "survey": {
                "code": self.target.code,
                "name": self.target.name,
                "dictionary_name": "WEIGHT_REUSE_UI_DICT",
                "source_table": "h0",
                "aggregate_only": True,
            },
            "variables": {"Q_B": {"label": "Uji", "values": {"1": "Ya"}}},
            "multiple_answer_groups": {},
            "build_report": {"contains_respondent_rows": False},
        }
        metadata = SurveyMetadataVersion.objects.create(
            survey=self.target,
            version="metadata_v1",
            questionnaire_key="WEIGHT_REUSE_UI_DICT",
            source_database="dbcs_weight_report",
            payload=payload,
            sha256=metadata_sha256(payload),
            is_active=True,
        )
        for code, readiness in (
            ("fieldwork_monitoring", SurveyEventModule.Readiness.READY),
            ("survey_analytics", SurveyEventModule.Readiness.READY),
            ("weighted_analysis", SurveyEventModule.Readiness.PENDING),
        ):
            SurveyEventModule.objects.create(
                survey=self.target,
                module=EventModuleDefinition.objects.get(code=code),
                readiness=readiness,
            )
        signature = event_configuration_signature(self.target, source, metadata)
        self.target.validation_report = {
            "final_rows": 2,
            "dataset_fingerprint": "a" * 64,
            "configuration_signature": signature,
            "errors": [],
        }
        self.target.save(update_fields=("validation_report",))
        SurveyMembership.objects.create(
            survey=self.target,
            user=self.staff,
            can_monitor=True,
            can_analyse=True,
            can_export=True,
        )

        self.source_survey = SurveyAccess.objects.create(
            code="weight_source26",
            name="Weight Source 2026",
            status=SurveyAccess.Status.ACTIVE,
            active=True,
        )
        self.source_weight = self._weight_set(
            survey=self.source_survey,
            version="raking_v1",
            fingerprint="a" * 64,
        )

    def _weight_set(self, *, survey, version, fingerprint):
        weight_set = SurveyWeightSet.objects.create(
            survey=survey,
            version=version,
            method="raking offline",
            key_column="Q_AC",
            weight_column="WEIGHT",
            file_sha256="b" * 64,
            dataset_fingerprint=fingerprint,
            source_row_count=2,
            matched_count=2,
            coverage=Decimal("100.0000"),
            weight_sum=Decimal("1.9000000000"),
            weight_min=Decimal("0.8000000000"),
            weight_max=Decimal("1.1000000000"),
            weight_mean=Decimal("0.9500000000"),
            effective_sample_size=Decimal("1.9500000000"),
            is_active=True,
        )
        SurveyWeight.objects.bulk_create(
            [
                SurveyWeight(weight_set=weight_set, respondent_key="1", weight="0.8"),
                SurveyWeight(weight_set=weight_set, respondent_key="2", weight="1.1"),
            ]
        )
        return weight_set

    def url(self):
        return reverse("aggregate:event_weighting_setup", args=(self.target.code,))

    def test_regular_user_cannot_open_weight_decision(self):
        self.client.force_login(self.regular)
        self.assertEqual(self.client.get(self.url()).status_code, 302)

    def test_compatible_source_is_offered(self):
        self.client.force_login(self.staff)
        response = self.client.get(self.url())
        self.assertContains(response, "weight_source26 - raking_v1")
        self.assertContains(response, "Dataset fingerprint")

    def test_reuse_clones_rows_and_records_lineage(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            self.url(),
            {"action": "reuse", "source_weight_set": self.source_weight.pk, "version": "raking_v1"},
        )
        self.assertRedirects(response, self.url())
        target_weight = SurveyWeightSet.objects.get(survey=self.target, version="raking_v1")
        self.assertTrue(target_weight.is_active)
        self.assertEqual(target_weight.parent_weight_set, self.source_weight)
        self.assertEqual(target_weight.weights.count(), 2)
        self.assertEqual(target_weight.weight_sum, self.source_weight.weight_sum)
        self.source_weight.refresh_from_db()
        self.assertTrue(self.source_weight.is_active)
        weighted = self.target.event_modules.get(module__code="weighted_analysis")
        self.assertEqual(weighted.readiness, SurveyEventModule.Readiness.READY)
        self.target.refresh_from_db()
        self.assertEqual(self.target.validation_state, SurveyAccess.ValidationState.PASSED)
        self.assertFalse(self.target.active)

    def test_incompatible_source_is_rejected(self):
        incompatible = self._weight_set(
            survey=self.source_survey,
            version="wrong_fingerprint",
            fingerprint="c" * 64,
        )
        self.client.force_login(self.staff)
        response = self.client.post(
            self.url(),
            {"action": "reuse", "source_weight_set": incompatible.pk, "version": "new"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Masukkan pilihan yang valid")
        self.assertFalse(SurveyWeightSet.objects.filter(survey=self.target).exists())

    def test_disable_resets_validation_for_required_rerun(self):
        self.client.force_login(self.staff)
        response = self.client.post(self.url(), {"action": "disable", "version": ""})
        self.assertRedirects(
            response,
            reverse("aggregate:event_final_validation", args=(self.target.code,)),
        )
        self.target.refresh_from_db()
        weighted = self.target.event_modules.get(module__code="weighted_analysis")
        self.assertFalse(weighted.enabled)
        self.assertEqual(self.target.validation_state, SurveyAccess.ValidationState.NOT_RUN)
        self.assertEqual(self.target.validation_report, {})
        self.assertEqual(self.target.validation_fingerprint, "")

    def test_activation_preview_passes_after_verified_reuse(self):
        self.client.force_login(self.staff)
        self.client.post(
            self.url(),
            {"action": "reuse", "source_weight_set": self.source_weight.pk, "version": "raking_v1"},
        )
        output = StringIO()
        call_command("activate_survey_event", survey=self.target.code, stdout=output)
        self.assertIn("Activation errors: 0", output.getvalue())
        self.target.refresh_from_db()
        self.assertFalse(self.target.active)
