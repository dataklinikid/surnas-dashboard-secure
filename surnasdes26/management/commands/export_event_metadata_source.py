import json
from contextlib import closing
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from aggregate.models import SurveyAccess, SurveyDataSource
from surnasdes26.services.legacy_db import (
    _mysql_driver,
    connect_database_config,
    get_data_source_config,
)


class Command(BaseCommand):
    help = (
        "Mengekspor dictionary CSPro dan schema h0 milik event dinamis tanpa "
        "mengekspor baris responden."
    )

    def add_arguments(self, parser):
        parser.add_argument("--survey", required=True, help="Kode event control plane.")
        parser.add_argument(
            "--output-dir",
            help="Folder keluaran; default local_artifacts/<survey>_metadata_source.",
        )

    def handle(self, *args, **options):
        survey_code = options["survey"].strip().lower()
        try:
            survey = SurveyAccess.objects.select_related("data_source").get(
                code=survey_code
            )
            source = survey.data_source
        except (SurveyAccess.DoesNotExist, SurveyDataSource.DoesNotExist) as exc:
            raise CommandError("Event atau data source tidak ditemukan.") from exc
        if not source.active:
            raise CommandError("Data source event tidak aktif.")

        config = get_data_source_config(source)
        output_value = options.get("output_dir") or (
            f"local_artifacts/{survey.code}_metadata_source"
        )
        output_dir = Path(output_value)
        if not output_dir.is_absolute():
            output_dir = settings.BASE_DIR / output_dir
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        mysql = _mysql_driver()
        try:
            with closing(connect_database_config(config)) as connection, closing(
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
                    (config["NAME"], config["TABLE"]),
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
                "Metadata event tidak dapat diekspor. Periksa cspro_meta, schema h0, "
                "tunnel, dan hak SELECT."
            ) from exc

        if not columns:
            raise CommandError("Schema tabel h0 tidak ditemukan.")
        if not meta_row or not meta_row.get("dictionary"):
            raise CommandError("Dictionary pada cspro_meta tidak ditemukan.")

        schema_payload = {
            "database_engine": "MariaDB",
            "database_version": server_version,
            "table": config["TABLE"],
            "column_count": len(columns),
            "columns": columns,
        }
        schema_path = output_dir / "h0_schema.json"
        schema_path.write_text(
            json.dumps(schema_payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        dictionary_path = output_dir / "cspro_dictionary.txt"
        dictionary_path.write_text(str(meta_row["dictionary"]), encoding="utf-8")
        manifest = {
            "survey_code": survey.code,
            "database_name": config["NAME"],
            "table": config["TABLE"],
            "column_count": len(columns),
            "source_modified_time": meta_row.get("source_modified_time"),
            "metadata_modified_time": meta_row.get("modified_time"),
            "contains_respondent_rows": False,
            "read_only_queries": 3,
            "files": [schema_path.name, dictionary_path.name],
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        self.stdout.write(self.style.SUCCESS("Ekspor sumber metadata event: OK"))
        self.stdout.write(f"Event: {survey.code}")
        self.stdout.write(f"Database: {config['NAME']}")
        self.stdout.write(f"Schema {config['TABLE']}: {len(columns)} kolom")
        self.stdout.write(f"Dictionary: {dictionary_path.name}")
        self.stdout.write("Baris responden diekspor: False")
        self.stdout.write("Read-only queries: 3")
        self.stdout.write(f"Output: {output_dir}")
