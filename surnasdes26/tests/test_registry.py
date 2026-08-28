from django.test import SimpleTestCase

from surnasdes26.services.metadata import load_metadata
from surnasdes26.services.registry import enabled_surveys, get_survey


class SurveyRegistryTests(SimpleTestCase):
    def test_surnasfeb26_is_registered(self):
        survey = get_survey("surnasfeb26")

        self.assertEqual(survey["database"]["alias"], "surnasdes26_db")
        self.assertEqual(survey["database"]["table"], "h0")
        self.assertEqual(survey["dataset"]["identity_column"], "Q_AC")
        self.assertTrue(survey["metadata"]["resolved_path"].is_file())

    def test_metadata_matches_registry(self):
        metadata = load_metadata("surnasfeb26")

        self.assertEqual(metadata["survey"]["code"], "surnasfeb26")
        self.assertEqual(len(metadata["variables"]), 299)

    def test_only_enabled_surveys_are_listed(self):
        codes = [survey["code"] for survey in enabled_surveys()]

        self.assertIn("surnasfeb26", codes)
