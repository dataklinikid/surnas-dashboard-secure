import json
import tempfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from surnasdes26.services.metadata import load_metadata
from surnasdes26.services.registry import SurveyRegistryError, get_survey
from surnasdes26.services.sectioning import classify_metadata_sections


def _atomic_write(path: Path, payload: dict) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(path)


class Command(BaseCommand):
    help = "Mengklasifikasikan section metadata secara aman. Default hanya preview."

    def add_arguments(self, parser):
        parser.add_argument("--survey-code", required=True)
        parser.add_argument("--reference-code")
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        survey_code = options["survey_code"].strip().lower()
        reference_code = str(options.get("reference_code") or "").strip().lower()
        if reference_code == survey_code:
            raise CommandError("Survey target dan referensi harus berbeda.")
        try:
            survey = get_survey(survey_code)
            target = load_metadata(survey_code)
            reference = load_metadata(reference_code) if reference_code else None
            result = classify_metadata_sections(target, reference)
        except (SurveyRegistryError, ValueError, OSError) as exc:
            raise CommandError(str(exc)) from exc

        action = "APPLIED" if options["apply"] else "PREVIEW"
        self.stdout.write(self.style.SUCCESS(f"Classify survey sections: {action}"))
        self.stdout.write(f"Survey code: {survey_code}")
        self.stdout.write(f"Reference code: {reference_code or '(tidak digunakan)'}")
        self.stdout.write(f"Variabel: {result['variable_count']}")
        self.stdout.write(f"Section berubah: {result['changed_count']}")
        self.stdout.write(f"Sumber klasifikasi: {result['source_counts']}")
        self.stdout.write(f"Distribusi section: {result['section_counts']}")

        if not options["apply"]:
            self.stdout.write("Metadata belum diubah. Tambahkan --apply untuk menerapkan.")
            return

        metadata_path = survey["metadata"]["resolved_path"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = (
            settings.BASE_DIR
            / "local_artifacts"
            / "metadata_backups"
            / f"{survey_code}_{timestamp}.json"
        )
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(backup_path, target)
        _atomic_write(metadata_path, result["metadata"])
        load_metadata.cache_clear()
        self.stdout.write(f"Backup metadata: {backup_path}")
        self.stdout.write(f"Metadata diperbarui: {metadata_path}")
