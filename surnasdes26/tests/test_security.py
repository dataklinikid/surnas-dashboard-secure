from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from aggregate.models import SurveyAccess, SurveyWeight, SurveyWeightSet
from aggregate.weighting import canonical_respondent_key, fingerprint_dataset
from surnasdes26.services.dataset import get_dataset


class SurveySecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="viewer", password="secure-test-password")

    def test_monitoring_requires_login(self):
        response = self.client.get(reverse("surnasdes26:monitoring"))
        self.assertEqual(response.status_code, 302)

    def test_analysis_denies_user_without_permission(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("surnasdes26:analysis"))
        self.assertEqual(response.status_code, 403)

    def test_analysis_accepts_authorized_user(self):
        permission = Permission.objects.get(codename="access_surnasdes26_analysis")
        self.user.user_permissions.add(permission)
        self.client.force_login(self.user)
        response = self.client.get(reverse("surnasdes26:analysis"))
        self.assertEqual(response.status_code, 200)

    def test_api_rejects_unlisted_variable(self):
        permission = Permission.objects.get(codename="access_surnasdes26_analysis")
        self.user.user_permissions.add(permission)
        self.client.force_login(self.user)
        response = self.client.get(reverse("surnasdes26:frequency_api"), {"variable": "PASSWORD"})
        self.assertEqual(response.status_code, 400)

    def test_generic_analysis_url_uses_survey_code(self):
        permission = Permission.objects.get(codename="access_surnasdes26_analysis")
        self.user.user_permissions.add(permission)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("surveys:analysis", kwargs={"survey_code": "surnasfeb26"})
        )

        self.assertEqual(response.status_code, 200)

    def test_multiple_answer_denies_user_without_analysis_access(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("surveys:multiple_answer", kwargs={"survey_code": "surnasfeb26"})
        )

        self.assertEqual(response.status_code, 403)

    def test_crosstab_denies_user_without_analysis_access(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("surveys:crosstab", kwargs={"survey_code": "surnasfeb26"})
        )

        self.assertEqual(response.status_code, 403)

    def test_generic_crosstab_accepts_authorized_user(self):
        permission = Permission.objects.get(codename="access_surnasdes26_analysis")
        self.user.user_permissions.add(permission)
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("surveys:crosstab", kwargs={"survey_code": "surnasfeb26"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Kasus valid berpasangan")

    def test_weighted_analysis_renders_active_weight_version(self):
        permission = Permission.objects.get(codename="access_surnasdes26_analysis")
        self.user.user_permissions.add(permission)
        self.client.force_login(self.user)
        survey = SurveyAccess.objects.get(code="surnasfeb26")
        dataset = get_dataset(force_refresh=True, survey_code="surnasfeb26")
        weight_set = SurveyWeightSet.objects.create(
            survey=survey,
            version="raking_test",
            method="test",
            key_column="Q_AC",
            weight_column="WEIGHT",
            file_sha256="0" * 64,
            dataset_fingerprint=fingerprint_dataset(dataset, "Q_AC", "H0_ID"),
            source_row_count=len(dataset),
            matched_count=len(dataset),
            coverage=100,
            weight_sum=len(dataset),
            weight_min=1,
            weight_max=1,
            weight_mean=1,
            effective_sample_size=len(dataset),
            is_active=True,
        )
        SurveyWeight.objects.bulk_create(
            [
                SurveyWeight(
                    weight_set=weight_set,
                    respondent_key=canonical_respondent_key(value),
                    weight=1,
                )
                for value in dataset["Q_AC"]
            ]
        )

        response = self.client.get(
            reverse("surveys:analysis", kwargs={"survey_code": "surnasfeb26"}),
            {"weighting": "weighted"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "raking_test")
        self.assertContains(response, "Weighted base")
        self.assertContains(response, "% tidak berbobot")
        self.assertContains(response, "% berbobot")

        crosstab_response = self.client.get(
            reverse("surveys:crosstab", kwargs={"survey_code": "surnasfeb26"}),
            {"weighting": "weighted", "output_type": "row_percentage"},
        )
        self.assertEqual(crosstab_response.status_code, 200)
        self.assertContains(crosstab_response, "Persentase per baris berbobot")
        self.assertNotContains(crosstab_response, "<small>n=")
