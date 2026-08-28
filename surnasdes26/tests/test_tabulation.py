import pandas as pd
from django.test import SimpleTestCase

from surnasdes26.services.tabulation import (
    InvalidTabulation,
    crosstab_table,
    frequency_table,
    multiple_answer_table,
)


class TabulationTests(SimpleTestCase):
    def setUp(self):
        self.df = pd.DataFrame({"Q2": [1, 1, 2, None], "Q3": [1, 2, 2, 1]})

    def test_frequency_total_and_percentage(self):
        result = frequency_table(self.df, "Q2", {"1": "L", "2": "P"})
        self.assertEqual(result["n_valid"], 3)
        self.assertEqual(sum(row["count"] for row in result["rows"]), 3)
        self.assertAlmostEqual(sum(row["percentage"] for row in result["rows"]), 100.0, places=1)

    def test_row_percentage_sums_to_100(self):
        result = crosstab_table(
            self.df,
            "Q2",
            "Q3",
            {"1": "L", "2": "P"},
            {"1": "Muda", "2": "Dewasa"},
            "row_percentage",
        )
        for row in result["rows"]:
            if row["n"]:
                self.assertAlmostEqual(sum(row["values"]), 100.0, places=1)
        self.assertEqual(result["n_total"], 4)
        self.assertEqual(result["n_valid"], 3)
        self.assertEqual(result["n_missing"], 1)
        self.assertEqual(result["grand_total"], 3)
        self.assertEqual(sum(result["column_totals"]), result["grand_total"])

    def test_crosstab_preserves_counts_for_percentage_output(self):
        result = crosstab_table(
            self.df,
            "Q2",
            "Q3",
            {"1": "L", "2": "P"},
            {"1": "Muda", "2": "Dewasa"},
            "column_percentage",
        )

        self.assertEqual(result["rows"][0]["cells"][0]["count"], 1)
        self.assertEqual(result["rows"][0]["cells"][1]["count"], 1)
        self.assertTrue(result["is_percentage"])

    def test_crosstab_rejects_same_variable(self):
        with self.assertRaises(InvalidTabulation):
            crosstab_table(self.df, "Q2", "Q2", {}, {}, "count")

    def test_invalid_output_is_rejected(self):
        with self.assertRaises(InvalidTabulation):
            crosstab_table(self.df, "Q2", "Q3", {}, {}, "invalid")

    def test_multiple_answer_uses_eligible_respondent_denominator(self):
        frame = pd.DataFrame(
            {
                "Q_XC(1)": [1, 0, None, 1],
                "Q_XC(2)": [0, 1, None, 1],
            }
        )
        specification = {
            "label": "Pilihan ganda",
            "selected_value": "1",
            "unselected_value": "0",
            "eligibility": "any_helper_not_blank",
            "options": [
                {"index": 1, "source_code": "A", "column": "Q_XC(1)", "label": "Opsi A"},
                {"index": 2, "source_code": "B", "column": "Q_XC(2)", "label": "Opsi B"},
            ],
        }

        result = multiple_answer_table(frame, "Q_X", specification)

        self.assertEqual(result["n_eligible"], 3)
        self.assertEqual(result["selection_total"], 4)
        self.assertEqual(result["rows"][0]["count"], 2)
        self.assertEqual(result["rows"][0]["percentage"], 66.7)
        self.assertEqual(result["mean_selections"], 1.33)

    def test_multiple_answer_rejects_missing_helper_column(self):
        specification = {
            "eligibility": "any_helper_not_blank",
            "options": [{"column": "Q_MISSING(1)", "label": "Hilang"}],
        }
        with self.assertRaises(InvalidTabulation):
            multiple_answer_table(self.df, "Q_MISSING", specification)

    def test_weighted_frequency_keeps_unweighted_count(self):
        frame = self.df.copy()
        frame["W"] = [0.5, 1.5, 2.0, 1.0]

        result = frequency_table(frame, "Q2", {"1": "L", "2": "P"}, "W")

        self.assertTrue(result["weighted"])
        self.assertEqual(result["weighted_base"], 4.0)
        self.assertEqual(result["rows"][0]["count"], 2.0)
        self.assertEqual(result["rows"][0]["unweighted_count"], 2)
        self.assertEqual(result["rows"][0]["unweighted_percentage"], 66.7)
        self.assertEqual(result["rows"][0]["percentage"], 50.0)

    def test_weighted_crosstab_uses_weights_for_percentages(self):
        frame = self.df.copy()
        frame["W"] = [1.0, 3.0, 2.0, 1.0]

        result = crosstab_table(
            frame,
            "Q2",
            "Q3",
            {"1": "L", "2": "P"},
            {"1": "Muda", "2": "Dewasa"},
            "row_percentage",
            "W",
        )

        self.assertTrue(result["weighted"])
        self.assertEqual(result["rows"][0]["cells"][0]["count"], 1)
        self.assertEqual(result["rows"][0]["cells"][0]["weighted_count"], 1.0)
        self.assertEqual(result["rows"][0]["cells"][0]["row_percentage"], 25.0)
        self.assertEqual(result["weighted_grand_total"], 6.0)
        self.assertEqual(result["output_label"], "Persentase per baris berbobot")
        self.assertEqual(result["row_total_label"], "Weighted total baris")
        self.assertTrue(result["show_row_total"])
        self.assertFalse(result["show_column_total"])
        self.assertEqual(result["rows"][0]["display_total"], 100.0)

    def test_weighted_multiple_answer_uses_weighted_eligible_base(self):
        frame = pd.DataFrame(
            {
                "Q_XC(1)": [1, 0, None],
                "Q_XC(2)": [0, 1, None],
                "W": [1.0, 3.0, 2.0],
            }
        )
        specification = {
            "label": "Pilihan ganda",
            "selected_value": "1",
            "eligibility": "any_helper_not_blank",
            "options": [
                {"column": "Q_XC(1)", "label": "A"},
                {"column": "Q_XC(2)", "label": "B"},
            ],
        }

        result = multiple_answer_table(frame, "Q_X", specification, "W")

        self.assertTrue(result["weighted"])
        self.assertEqual(result["n_eligible"], 2)
        self.assertEqual(result["weighted_eligible"], 4.0)
        self.assertEqual(result["rows"][0]["percentage"], 25.0)
