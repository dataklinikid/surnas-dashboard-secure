import hashlib
import json
import os
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from aggregate.models import (
    Region,
    SurveyAccess,
    SurveyConnectionProfile,
    SurveyDataSource,
    SurveyMetadataVersion,
    SurveyProgram,
)
from surnasdes26.services.registry import SurveyRegistryError, get_survey


def canonical_metadata_sha256(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_optional_date(value: str | None, option_name: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CommandError(f"{option_name} harus menggunakan format YYYY-MM-DD.") from exc


class Command(BaseCommand):
    help = (
        "Menyinkronkan satu manifest Survey Registry ke control plane PostgreSQL. "
        "Default hanya preview; gunakan --apply untuk menyimpan."
    )

    def add_arguments(self, parser):
        parser.add_argument("--survey", required=True, help="Kode event pada Survey Registry.")
        parser.add_argument("--program-code", required=True)
        parser.add_argument("--program-name", required=True)
        parser.add_argument("--region-code", required=True)
        parser.add_argument("--region-name", required=True)
        parser.add_argument(
            "--region-level",
            required=True,
            choices=[value for value, _label in Region.Level.choices],
        )
        parser.add_argument("--metadata-version", required=True)
        parser.add_argument("--period-start")
        parser.add_argument("--period-end")
        parser.add_argument(
            "--database-name",
            help="Override nama database; default membaca <ENV_PREFIX>_NAME.",
        )
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        survey_code = options["survey"].strip().lower()
        try:
            manifest = get_survey(survey_code)
        except SurveyRegistryError as exc:
            raise CommandError(str(exc)) from exc

        metadata_path = manifest["metadata"]["resolved_path"]
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Metadata tidak dapat dibaca: {metadata_path}.") from exc
        if not isinstance(metadata, dict) or not isinstance(metadata.get("variables"), dict):
            raise CommandError("Metadata harus berupa object dan memiliki object 'variables'.")

        database = manifest["database"]
        env_prefix = database["env_prefix"]
        database_name = (options.get("database_name") or os.getenv(f"{env_prefix}_NAME", "")).strip()
        if not database_name:
            raise CommandError(
                f"Nama database belum tersedia. Isi {env_prefix}_NAME atau gunakan --database-name."
            )

        period_start = parse_optional_date(options.get("period_start"), "--period-start")
        period_end = parse_optional_date(options.get("period_end"), "--period-end")
        if period_start and period_end and period_end < period_start:
            raise CommandError("--period-end tidak boleh lebih awal daripada --period-start.")

        program_values = {
            "code": options["program_code"].strip().lower(),
            "name": options["program_name"].strip(),
            "active": True,
        }
        region_values = {
            "code": options["region_code"].strip().lower(),
            "name": options["region_name"].strip(),
            "level": options["region_level"],
            "active": True,
        }
        survey_values = {
            "code": manifest["code"],
            "name": manifest["name"],
            "period_start": period_start,
            "period_end": period_end,
            "dashboard_config": manifest.get("dashboard", {}),
            "privacy_config": manifest.get("privacy", {"aggregate_only": True}),
            "status": SurveyAccess.Status.ACTIVE,
            "active": bool(manifest["enabled"]),
        }
        dataset = manifest["dataset"]
        source_values = {
            "engine": SurveyDataSource.Engine.MARIADB,
            "connection_alias": database["alias"],
            "environment_prefix": env_prefix,
            "database_name": database_name,
            "table_name": database["table"],
            "identity_column": dataset["identity_column"],
            "latest_id_column": dataset.get("latest_id_column", ""),
            "valid_column": settings.SURNAS_VALID_COLUMN,
            "valid_value": settings.SURNAS_VALID_VALUE,
            "target_n": dataset.get("target_n"),
            "active": bool(manifest["enabled"]),
        }
        metadata_values = {
            "version": options["metadata_version"].strip().lower(),
            "metadata_schema_version": int(metadata.get("metadata_schema_version", 1)),
            "questionnaire_key": str(
                metadata.get("survey", {}).get("dictionary_name", "")
            ).strip().upper(),
            "source_database": database_name.casefold(),
            "payload": metadata,
            "sha256": canonical_metadata_sha256(metadata),
            "source_name": metadata_path.name,
            "is_active": True,
        }
        if not metadata_values["questionnaire_key"]:
            raise CommandError(
                "Metadata harus memiliki survey.dictionary_name sebagai identitas kuesioner."
            )

        self._validate_preview(
            program_values,
            region_values,
            survey_values,
            source_values,
            metadata_values,
        )
        existing = SurveyAccess.objects.filter(code=survey_code).first()

        self.stdout.write("Sinkronisasi konfigurasi event: PREVIEW" if not options["apply"] else "Sinkronisasi konfigurasi event: APPLY")
        self.stdout.write(f"Survey code: {survey_code}")
        self.stdout.write(f"Survey existing: {'ya' if existing else 'tidak'}")
        self.stdout.write(f"Program: {program_values['code']} - {program_values['name']}")
        self.stdout.write(f"Region: {region_values['code']} - {region_values['name']}")
        self.stdout.write(f"Database alias: {source_values['connection_alias']}")
        self.stdout.write(f"Database name: {source_values['database_name']}")
        self.stdout.write(f"Table: {source_values['table_name']}")
        self.stdout.write(f"Identity/latest: {source_values['identity_column']} / {source_values['latest_id_column'] or '-'}")
        self.stdout.write(f"Target n: {source_values['target_n'] if source_values['target_n'] is not None else '-'}")
        self.stdout.write(f"Metadata version: {metadata_values['version']}")
        self.stdout.write(f"Metadata SHA256: {metadata_values['sha256']}")
        self.stdout.write(f"Variabel metadata: {len(metadata['variables'])}")
        if existing:
            self.stdout.write(f"Membership dipertahankan: {existing.memberships.count()}")
            self.stdout.write(f"Weight set dipertahankan: {existing.weight_sets.count()}")

        if not options["apply"]:
            self.stdout.write("Preview selesai; PostgreSQL belum diubah.")
            return

        with transaction.atomic():
            program, _ = SurveyProgram.objects.update_or_create(
                code=program_values.pop("code"),
                defaults=program_values,
            )
            region, _ = Region.objects.update_or_create(
                code=region_values.pop("code"),
                defaults=region_values,
            )
            survey_values.update(program=program, region=region)
            survey, _ = SurveyAccess.objects.update_or_create(
                code=survey_values.pop("code"),
                defaults=survey_values,
            )
            connection_profile, _ = SurveyConnectionProfile.objects.get_or_create(
                code=source_values["connection_alias"],
                defaults={
                    "name": source_values["connection_alias"].replace("_", " ").title(),
                    "engine": source_values["engine"],
                    "environment_prefix": source_values["environment_prefix"],
                    "description": "Dibentuk dari sinkronisasi Survey Registry.",
                    "active": True,
                },
            )
            source_values["connection_profile"] = connection_profile
            SurveyDataSource.objects.update_or_create(
                survey=survey,
                defaults=source_values,
            )
            SurveyMetadataVersion.objects.filter(survey=survey, is_active=True).exclude(
                version=metadata_values["version"]
            ).update(is_active=False)
            version = metadata_values.pop("version")
            SurveyMetadataVersion.objects.update_or_create(
                survey=survey,
                version=version,
                defaults=metadata_values,
            )

        self.stdout.write(self.style.SUCCESS("Sinkronisasi konfigurasi event: APPLIED"))
        self.stdout.write("Runtime registry: JSON fallback masih aktif")

    @staticmethod
    def _validate_preview(program, region, survey, source, metadata):
        candidates = (
            SurveyProgram(**program),
            Region(**region),
            SurveyAccess(**survey),
            SurveyDataSource(survey=SurveyAccess(**survey), **source),
            SurveyMetadataVersion(survey=SurveyAccess(**survey), **metadata),
        )
        try:
            for candidate in candidates:
                candidate.full_clean(
                    exclude={"survey"} if hasattr(candidate, "survey_id") else None,
                    validate_unique=False,
                    validate_constraints=False,
                )
        except ValidationError as exc:
            raise CommandError(f"Konfigurasi tidak valid: {exc.message_dict}") from exc
