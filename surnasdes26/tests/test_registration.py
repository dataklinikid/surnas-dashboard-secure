import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, override_settings

from surnasdes26.services.metadata import load_metadata
from surnasdes26.services.registration import apply_registration, build_registration_plan
from surnasdes26.services.registry import clear_registry_cache, get_survey


class SurveyRegistrationTests(SimpleTestCase):
    def tearDown(self):
        clear_registry_cache()
        load_metadata.cache_clear()

    def test_existing_survey_is_replaced_with_backup_and_preserved_section(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = root / "config" / "surveys"
            old_metadata = root / "old" / "metadata.json"
            registry.mkdir(parents=True)
            old_metadata.parent.mkdir(parents=True)
            old_metadata.write_text(
                json.dumps({"survey": {"code": "contoh26"}, "variables": {"Q_1": {"section": "Bagian lama"}}}),
                encoding="utf-8",
            )
            manifest = {
                "schema_version": 1,
                "code": "contoh26",
                "name": "Lama",
                "enabled": True,
                "database": {"alias": "contoh26_db", "env_prefix": "CONTOH26_DB", "table": "h0", "legacy_source": True},
                "metadata": {"path": "old/metadata.json"},
                "dataset": {"identity_column": "Q_AC", "latest_id_column": "H0_ID", "target_n": 100},
                "privacy": {"aggregate_only": True},
            }
            (registry / "contoh26.json").write_text(json.dumps(manifest), encoding="utf-8")
            canonical = {
                "metadata_schema_version": 1,
                "survey": {"code": "contoh26", "name": "Baru", "source_table": "h0", "aggregate_only": True},
                "variables": {"Q_1": {"label": "Gender", "section": "Otomatis", "values": {"1": "L"}}},
                "multiple_answer_groups": {},
                "build_report": {"contains_respondent_rows": False},
            }
            canonical_path = root / "canonical.json"
            canonical_path.write_text(json.dumps(canonical), encoding="utf-8")

            with override_settings(
                BASE_DIR=root,
                SURVEY_REGISTRY_DIR=registry,
                ACTIVE_SURVEY_CODE="contoh26",
            ):
                clear_registry_cache()
                load_metadata.cache_clear()
                plan = build_registration_plan(canonical_path)
                result = apply_registration(plan, replace=True)
                survey = get_survey("contoh26")
                metadata = load_metadata("contoh26")

            self.assertIsNotNone(result["backup_path"])
            self.assertTrue(result["backup_path"].is_file())
            self.assertEqual(survey["metadata"]["resolved_path"], root / "survey_metadata" / "contoh26" / "metadata.json")
            self.assertEqual(metadata["variables"]["Q_1"]["section"], "Bagian lama")
            self.assertNotIn("password", json.dumps(result["manifest"]).lower())
