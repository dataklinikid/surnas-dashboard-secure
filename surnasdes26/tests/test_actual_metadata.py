from django.test import SimpleTestCase

from surnasdes26.services.metadata import (
    allowed_variables,
    grouped_variable_choices,
    multiple_answer_groups,
)


class ActualMetadataTests(SimpleTestCase):
    def test_actual_dictionary_allowlist_is_used(self):
        variables = allowed_variables()

        self.assertEqual(len(variables), 299)
        self.assertEqual(variables["Q_B"]["values"]["1"], "Laki-laki")
        self.assertEqual(variables["Q_F"]["values"]["38"], "Papua Pegunungan")

    def test_direct_identifiers_and_free_text_are_excluded(self):
        variables = allowed_variables()

        for variable in ("Q_G", "Q_I", "Q_J", "Q_V", "Q_W", "Q_AC", "HPID", "USRNM"):
            self.assertNotIn(variable, variables)

    def test_choices_are_grouped_by_section(self):
        groups = grouped_variable_choices({"Q_B", "Q_4"})

        self.assertEqual(len(groups), 2)
        self.assertTrue(all(group["choices"] for group in groups))

    def test_multiple_answer_groups_are_loaded_from_canonical_metadata(self):
        groups = multiple_answer_groups("surnasfeb26")

        self.assertEqual(len(groups), 7)
        self.assertEqual(groups["Q_34"]["helper_prefix"], "Q_34C")
        self.assertEqual(groups["Q_34"]["eligibility"], "any_helper_not_blank")
