import pandas as pd
from django.test import SimpleTestCase, override_settings

from surnasdes26.services.dataset import prepare_dataset


class DatasetPreparationTests(SimpleTestCase):
    @override_settings(SURNAS_VALID_COLUMN="Q_V", SURNAS_VALID_VALUE="OK")
    def test_latest_duplicate_and_valid_status_are_used(self):
        raw = pd.DataFrame(
            {
                "h0_id": [1, 2, 3],
                "q_ac": [10, 10, 11],
                "q_v": ["REVIEW", "OK", "OK"],
                "q_2": [1, 2, 1],
            }
        )
        result = prepare_dataset(raw)
        self.assertEqual(result["Q_AC"].tolist(), [10, 11])
        self.assertEqual(result.loc[result["Q_AC"] == 10, "Q_2"].iloc[0], 2)
