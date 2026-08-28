import pandas as pd
from django.test import SimpleTestCase
from unittest.mock import patch

from surnasdes26.services.legacy_db import get_database_config, normalize_source_columns


class LegacyColumnNormalizationTests(SimpleTestCase):
    def test_cspro_relation_ids_are_normalized(self):
        frame = pd.DataFrame({"h0-id": [3], "level-1-id": [8], "q_ac": [1001]})

        normalized = normalize_source_columns(frame)

        self.assertIn("h0_id", normalized.columns)
        self.assertIn("level_1_id", normalized.columns)
        self.assertNotIn("h0-id", normalized.columns)

    @patch.dict(
        "os.environ",
        {
            "SURNAS_DB_NAME": "db_report",
            "SURNAS_DB_USER": "reader",
            "SURNAS_DB_PASSWORD": "secret-test-only",
            "SURNAS_DB_HOST": "127.0.0.1",
            "SURNAS_DB_PORT": "3307",
        },
        clear=False,
    )
    def test_database_config_uses_registry_environment_prefix(self):
        config = get_database_config("surnasfeb26")

        self.assertEqual(config["NAME"], "db_report")
        self.assertEqual(config["USER"], "reader")
        self.assertEqual(config["PORT"], 3307)
        self.assertEqual(config["TABLE"], "h0")
