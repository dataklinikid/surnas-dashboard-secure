from django.test import SimpleTestCase

from surnasdes26.services.sectioning import (
    classify_metadata_sections,
    sections_are_informative,
)


class SectioningTests(SimpleTestCase):
    def test_identical_variables_copy_reference_sections_exactly(self):
        target = {
            "variables": {
                "Q_1": {"label": "Jenis kelamin", "section": "Demografi responden"},
                "Q_2": {"label": "Pilihan partai", "section": "Demografi responden"},
            }
        }
        reference = {
            "variables": {
                "Q_1": {"section": "Demografi dan karakteristik responden"},
                "Q_2": {"section": "Politik dan elektoral"},
            }
        }

        result = classify_metadata_sections(target, reference)

        self.assertEqual(result["source_counts"], {"reference": 2})
        self.assertEqual(result["changed_count"], 2)
        self.assertEqual(
            result["metadata"]["variables"]["Q_2"]["section"],
            "Politik dan elektoral",
        )

    def test_semantic_fallback_handles_different_questionnaire(self):
        target = {
            "variables": {
                "D1": {"label": "Berapa usia responden?", "section": "Level 1"},
                "P1": {"label": "Pilihan partai saat ini", "section": "Level 1"},
                "M1": {"label": "Sumber informasi media sosial", "section": "Level 1"},
            }
        }

        result = classify_metadata_sections(target)

        self.assertEqual(result["source_counts"], {"semantic": 3})
        self.assertEqual(
            result["metadata"]["variables"]["D1"]["section"],
            "Demografi dan karakteristik responden",
        )
        self.assertEqual(
            result["metadata"]["variables"]["P1"]["section"],
            "Politik dan elektoral",
        )

    def test_informative_existing_sections_are_preserved(self):
        target = {
            "variables": {
                "A": {"label": "Variabel A", "section": "Bagian A"},
                "B": {"label": "Variabel B", "section": "Bagian B"},
            }
        }

        result = classify_metadata_sections(target)

        self.assertTrue(sections_are_informative(target))
        self.assertEqual(result["source_counts"], {"existing": 2})
        self.assertEqual(result["changed_count"], 0)

    def test_explicit_preserve_keeps_single_curated_section(self):
        target = {
            "variables": {
                "D1": {"label": "Usia responden", "section": "Bagian kurasi"},
            }
        }

        result = classify_metadata_sections(target, preserve_current=True)

        self.assertEqual(result["source_counts"], {"existing": 1})
        self.assertEqual(
            result["metadata"]["variables"]["D1"]["section"],
            "Bagian kurasi",
        )
