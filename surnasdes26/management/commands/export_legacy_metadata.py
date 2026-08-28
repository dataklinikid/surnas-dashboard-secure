import json
from contextlib import closing
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from surnasdes26.services.legacy_db import _mysql_driver, connect_legacy, get_database_config
from surnasdes26.services.registry import get_survey


class Command(BaseCommand):
    help = "Mengekspor schema dan dictionary CSPro tanpa data responden berdasarkan registry."

    def add_arguments(self, parser):
        parser.add_argument("--survey", help="Survey code; default ACTIVE_SURVEY_CODE.")
        parser.add_argument("--output-dir", help="Folder keluaran relatif terhadap root project.")

    def handle(self, *args, **options):
        try:
            survey = get_survey(options.get("survey"))
            config = get_database_config(survey["code"])
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        if not survey["database"].get("legacy_source", True):
            raise CommandError("Command ini hanya tersedia pada mode sumber legacy.")

        output_value = options.get("output_dir") or f"local_artifacts/{survey['code']}_metadata"
        output_dir = (settings.BASE_DIR / output_value).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        mysql = _mysql_driver()
        database_name = config["NAME"]
        table_name = config["TABLE"]
        try:
            with closing(connect_legacy(survey["code"])) as connection, closing(
                connection.cursor(mysql.cursors.DictCursor)
            ) as cursor:
                cursor.execute("SELECT VERSION() AS version")
                server_version = str(cursor.fetchone()["version"])

                cursor.execute(
                    """
                    SELECT
                        COLUMN_NAME,
                        ORDINAL_POSITION,
                        COLUMN_TYPE,
                        IS_NULLABLE,
                        COLUMN_KEY,
                        EXTRA,
                        CHARACTER_SET_NAME,
                        COLLATION_NAME,
                        COLUMN_COMMENT
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                    """,
                    (database_name, table_name),
                )
                columns = [dict(row) for row in cursor.fetchall()]

                cursor.execute(
                    """
                    SELECT dictionary, source_modified_time, modified_time
                    FROM cspro_meta
                    ORDER BY modified_time DESC
                    LIMIT 1
                    """
                )
                meta_row = cursor.fetchone()
        except Exception as exc:
            raise CommandError(
                f"Metadata legacy tidak dapat diekspor ({exc.__class__.__name__}: {exc})."
            ) from exc

        if not columns:
            raise CommandError("Schema tabel h0 tidak ditemukan.")
        if not meta_row or not meta_row.get("dictionary"):
            raise CommandError("Dictionary pada cspro_meta tidak ditemukan.")

        schema_payload = {
            "database_engine": "MariaDB",
            "database_version": server_version,
            "table": table_name,
            "column_count": len(columns),
            "columns": columns,
        }
        schema_path = output_dir / "h0_schema.json"
        schema_path.write_text(
            json.dumps(schema_payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        dictionary_text = str(meta_row["dictionary"])
        try:
            dictionary_payload = json.loads(dictionary_text)
        except json.JSONDecodeError:
            dictionary_path = output_dir / "cspro_dictionary.txt"
            dictionary_path.write_text(dictionary_text, encoding="utf-8")
        else:
            dictionary_path = output_dir / "cspro_dictionary.json"
            dictionary_path.write_text(
                json.dumps(dictionary_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        manifest = {
            "database_version": server_version,
            "survey_code": survey["code"],
            "table": table_name,
            "column_count": len(columns),
            "source_modified_time": meta_row.get("source_modified_time"),
            "metadata_modified_time": meta_row.get("modified_time"),
            "contains_respondent_rows": False,
            "files": [schema_path.name, dictionary_path.name],
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        self.stdout.write(self.style.SUCCESS(f"Metadata tersimpan di: {output_dir}"))
        self.stdout.write(self.style.SUCCESS(f"Schema {table_name}: {len(columns)} kolom"))
        self.stdout.write(self.style.SUCCESS(f"Dictionary: {dictionary_path.name}"))
        self.stdout.write("Tidak ada baris jawaban responden yang diekspor.")
