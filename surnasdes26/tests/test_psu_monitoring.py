from unittest import TestCase

import pandas as pd

from surnasdes26.services.monitoring import psu_monitoring_summary


class PSUMonitoringSummaryTests(TestCase):
    def test_targets_are_per_psu_and_linkage_is_by_unique_questionnaire_number(self):
        frame_rows = [
            {"psu_number": 1, "village": "A", "district": "D1", "regency": "R1", "dpr_ri_constituency": "X", "province": "P", "urban_rural": "KOTA", "target_n": 8, "questionnaire_start": 1, "questionnaire_end": 8},
            {"psu_number": 2, "village": "B", "district": "D2", "regency": "R2", "dpr_ri_constituency": "X", "province": "P", "urban_rural": "DESA", "target_n": 15, "questionnaire_start": 9, "questionnaire_end": 23},
        ]
        monitoring = {
            "columns": {"questionnaire": "NO_KUES", "enumerator": "ENUM"},
            "psu_frame": {"version": "v1", "target_total": 23, "rows": frame_rows},
        }
        df = pd.DataFrame(
            {
                "NO_KUES": [1, 2, 2, 9, 23, 24, None, 1.5],
                "ENUM": ["A", "A", "TYPO", "B", "B", "C", "D", "E"],
            }
        )
        result = psu_monitoring_summary(df, monitoring)
        self.assertEqual(result["target"], 23)
        self.assertEqual(result["actual"], 4)
        self.assertEqual(result["psu_rows"][0]["target_n"], 8)
        self.assertEqual(result["psu_rows"][1]["target_n"], 15)
        self.assertEqual(result["unmatched"], 1)
        self.assertEqual(result["missing_questionnaire"], 2)
        self.assertEqual(result["duplicate_rows"], 2)
        self.assertEqual(result["enumerator_rows"], [{"label": "A", "actual": 2}, {"label": "B", "actual": 2}])

    def test_missing_frame_or_mapping_returns_none(self):
        df = pd.DataFrame({"Q": [1]})
        self.assertIsNone(psu_monitoring_summary(df, {}))
        self.assertIsNone(
            psu_monitoring_summary(df, {"psu_frame": {"rows": []}, "columns": {}})
        )
