from unittest import TestCase

from aggregate.multiple_answer_revision import revise_compact_groups
from aggregate.management.commands.revise_multiple_answer_storage import Command


class MultipleAnswerRevisionTests(TestCase):
    def test_command_parser_uses_non_conflicting_metadata_version_option(self):
        parser = Command().create_parser("manage.py", "revise_multiple_answer_storage")
        values = parser.parse_args(
            [
                "--survey",
                "provntt_nov24",
                "--groups",
                "Q_61_1",
                "--eligibility",
                "all_respondents",
                "--metadata-version",
                "metadata_v2",
            ]
        )
        self.assertEqual(values.metadata_version, "metadata_v2")

    def test_revision_preserves_options_and_sets_compact_contract(self):
        payload = {
            "multiple_answer_groups": {
                "Q_61_1": {
                    "eligibility": "any_helper_not_blank",
                    "options": [
                        {"source_code": "1", "column": "Q_61_1C(1)"},
                        {"source_code": "2", "column": "Q_61_1C(2)"},
                    ],
                }
            }
        }

        revised = revise_compact_groups(payload, ["Q_61_1"], "all_respondents")

        group = revised["multiple_answer_groups"]["Q_61_1"]
        self.assertEqual(group["storage"], "compact_codes")
        self.assertEqual(group["source_column"], "Q_61_1")
        self.assertEqual(group["eligibility"], "all_respondents")
        self.assertNotIn("storage", payload["multiple_answer_groups"]["Q_61_1"])
