from django.test import SimpleTestCase

from surnasdes26.models import H0
from surnasdes26.routers import SurveyReportingRouter


class SurveyRouterTests(SimpleTestCase):
    def test_read_routes_to_reporting_database(self):
        self.assertEqual(SurveyReportingRouter().db_for_read(H0), "surnasdes26_db")

    def test_migration_is_always_blocked(self):
        router = SurveyReportingRouter()
        self.assertFalse(router.allow_migrate("surnasdes26_db", "surnasdes26"))
        self.assertFalse(router.allow_migrate("default", "surnasdes26"))
