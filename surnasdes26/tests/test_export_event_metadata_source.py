import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from aggregate.models import SurveyAccess, SurveyDataSource


class ExportEventMetadataSourceTests(TestCase):
    def setUp(self):
        seed = SurveyAccess.objects.get(code="surnasfeb26")
        self.survey = SurveyAccess.objects.create(
            code="provntt_nov24",
            name="Survei Provinsi NTT November 2024",
            status=SurveyAccess.Status.DRAFT,
            active=False,
        )
        SurveyDataSource.objects.create(
            survey=self.survey,
            connection_alias="csweb_catalog",
            environment_prefix="CSWEB_CATALOG_DB",
            database_name="dbcs76_provntt_report",
            table_name="h0",
            active=True,
        )
        self.seed = seed

    def test_export_uses_three_read_only_queries_and_writes_no_rows(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"version": "10.4.33-MariaDB"},
            {
                "dictionary": "[Dictionary]\nName=PROVNTT_NOV24_DICT\n",
                "source_modified_time": "2024-11-01",
                "modified_time": "2024-11-02",
            },
        ]
        cursor.fetchall.return_value = [
            {
                "COLUMN_NAME": "Q_AC",
                "ORDINAL_POSITION": 1,
                "COLUMN_TYPE": "varchar(32)",
                "IS_NULLABLE": "NO",
                "COLUMN_KEY": "",
                "EXTRA": "",
                "CHARACTER_SET_NAME": "utf8mb4",
                "COLLATION_NAME": "utf8mb4_general_ci",
                "COLUMN_COMMENT": "",
            }
        ]
        connection = MagicMock()
        connection.cursor.return_value = cursor
        mysql = MagicMock()

        with tempfile.TemporaryDirectory() as temporary:
            output = StringIO()
            with patch(
                "surnasdes26.management.commands.export_event_metadata_source.get_data_source_config",
                return_value={
                    "NAME": "dbcs76_provntt_report",
                    "TABLE": "h0",
                },
            ), patch(
                "surnasdes26.management.commands.export_event_metadata_source.connect_database_config",
                return_value=connection,
            ), patch(
                "surnasdes26.management.commands.export_event_metadata_source._mysql_driver",
                return_value=mysql,
            ):
                call_command(
                    "export_event_metadata_source",
                    survey=self.survey.code,
                    output_dir=temporary,
                    stdout=output,
                )

            directory = Path(temporary)
            manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
            self.assertEqual(manifest["database_name"], "dbcs76_provntt_report")
            self.assertFalse(manifest["contains_respondent_rows"])
            self.assertEqual(manifest["read_only_queries"], 3)
            self.assertTrue((directory / "h0_schema.json").is_file())
            self.assertTrue((directory / "cspro_dictionary.txt").is_file())
            self.assertEqual(cursor.execute.call_count, 3)
            self.assertIn("Baris responden diekspor: False", output.getvalue())
