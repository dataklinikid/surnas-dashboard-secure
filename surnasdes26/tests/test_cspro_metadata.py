import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from surnasdes26.services.cspro_metadata import build_canonical_metadata


DICTIONARY = """[Dictionary]
Version=CSPro 7.7
Label=Contoh
Name=CONTOH_DICT

[Record]
Label=Demografi
Name=H0

[Item]
Label=Jenis kelamin
Name=Q_1
DataType=Numeric

[ValueSet]
Value=1;Laki-laki
Value=2;Perempuan

[Item]
Label=Sumber informasi [boleh lebih dari satu]
Name=Q_2
DataType=Alpha

[ValueSet]
Value='A ';Televisi (1)
Value='B ';Media sosial (2)

[Item]
Label=Q_2C. Multiple Answer
Name=Q_2C
DataType=Numeric
Occurrences=2
"""


class CsproMetadataTests(SimpleTestCase):
    def test_dictionary_and_schema_become_canonical_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "cspro_dictionary.txt").write_text(DICTIONARY, encoding="utf-8")
            schema = {
                "table": "h0",
                "columns": [
                    {"COLUMN_NAME": "q_1"},
                    {"COLUMN_NAME": "q_2"},
                    {"COLUMN_NAME": "q_2c(1)"},
                    {"COLUMN_NAME": "q_2c(2)"},
                ],
            }
            (source / "h0_schema.json").write_text(json.dumps(schema), encoding="utf-8")

            payload = build_canonical_metadata(source, "contoh26", "Survei Contoh")

        self.assertEqual(payload["variables"]["Q_1"]["values"]["2"], "Perempuan")
        group = payload["multiple_answer_groups"]["Q_2"]
        self.assertEqual(group["helper_prefix"], "Q_2C")
        self.assertEqual(group["options"][1]["label"], "Media sosial")
        self.assertEqual(group["eligibility"], "any_helper_not_blank")
        self.assertFalse(payload["build_report"]["contains_respondent_rows"])
