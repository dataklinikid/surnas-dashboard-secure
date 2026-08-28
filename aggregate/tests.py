from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from aggregate.models import SurveyAccess, SurveyMembership


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
