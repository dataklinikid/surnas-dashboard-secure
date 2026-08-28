import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from surnasdes26.services.cspro_metadata import MetadataParseError, build_canonical_metadata


class Command(BaseCommand):
    help = "Mengubah dictionary CSPro dan schema mirror menjadi metadata canonical tanpa mengubah registry."

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True, help="ZIP/folder berisi dictionary dan schema.")
        parser.add_argument("--code", required=True, help="Survey code, contoh surnasfeb26.")
        parser.add_argument("--name", required=True, help="Nama kegiatan survei.")
        parser.add_argument(
            "--output",
            help="File JSON keluaran; default local_artifacts/<code>_canonical_metadata.json.",
        )

    def handle(self, *args, **options):
        try:
            payload = build_canonical_metadata(
                source=options["source"],
                survey_code=options["code"],
                survey_name=options["name"],
            )
        except (MetadataParseError, OSError, json.JSONDecodeError) as exc:
            raise CommandError(str(exc)) from exc

        output_value = options.get("output") or (
            f"local_artifacts/{payload['survey']['code']}_canonical_metadata.json"
        )
        output_path = Path(output_value)
        if not output_path.is_absolute():
            output_path = settings.BASE_DIR / output_path
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        report = payload["build_report"]
        self.stdout.write(self.style.SUCCESS("Parsing metadata canonical: OK"))
        self.stdout.write(f"Survey code: {payload['survey']['code']}")
        self.stdout.write(f"Dictionary items: {report['dictionary_item_count']}")
        self.stdout.write(f"Schema columns: {report['schema_column_count']}")
        self.stdout.write(f"Variabel kategorik: {report['categorical_variable_count']}")
        self.stdout.write(f"Kelompok multiple-answer: {report['multiple_answer_group_count']}")
        self.stdout.write(f"Baris responden diekspor: {report['contains_respondent_rows']}")
        self.stdout.write(f"Output: {output_path}")
