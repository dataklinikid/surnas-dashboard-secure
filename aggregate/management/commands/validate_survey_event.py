import hashlib
import json

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from aggregate.models import SurveyAccess, SurveyDataSource
from aggregate.event_validation import event_configuration_signature
from aggregate.module_readiness import refresh_event_module_readiness
from aggregate.weighting import fingerprint_dataset
from surnasdes26.services.legacy_db import read_data_source
from surnasdes26.services.runtime import metadata_sha256


class Command(BaseCommand):
    help = (
        "Memvalidasi kontrak event PostgreSQL terhadap database reporting. "
        "Default preview; --apply menyimpan status dan laporan tanpa mengaktifkan event."
    )

    def add_arguments(self, parser):
        parser.add_argument("--survey", required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        code = options["survey"].strip().lower()
        try:
            survey = SurveyAccess.objects.select_related("data_source").get(code=code)
            source = survey.data_source
        except (SurveyAccess.DoesNotExist, SurveyDataSource.DoesNotExist) as exc:
            raise CommandError("Event atau data source tidak ditemukan.") from exc

        metadata_rows = list(survey.metadata_versions.filter(is_active=True)[:2])
        errors = []
        warnings = []
        metadata = metadata_rows[0] if len(metadata_rows) == 1 else None
        if metadata is None:
            errors.append("Event harus memiliki tepat satu metadata aktif.")
            payload = {}
        else:
            payload = metadata.payload
            if metadata_sha256(payload) != metadata.sha256:
                errors.append("Checksum metadata tidak cocok.")
            survey_payload = payload.get("survey", {})
            metadata_code = str(survey_payload.get("code", "")).strip().lower()
            if metadata_code != survey.code:
                errors.append("Kode event pada metadata tidak cocok.")
            questionnaire_key = str(
                survey_payload.get("dictionary_name", "")
            ).strip().upper()
            if questionnaire_key != metadata.questionnaire_key:
                errors.append("Identitas kuesioner pada metadata tidak cocok.")
            if metadata.source_database != source.database_name.casefold():
                errors.append("Ikatan database pada metadata tidak cocok dengan data source event.")
            aggregate_only = payload.get("privacy", {}).get(
                "aggregate_only",
                survey_payload.get("aggregate_only"),
            )
            contains_rows = payload.get("build_report", {}).get("contains_respondent_rows")
            if aggregate_only is not True:
                errors.append("Metadata harus menggunakan aggregate_only=true.")
            if contains_rows is not False:
                errors.append("Metadata harus menggunakan contains_respondent_rows=false.")

        try:
            raw = read_data_source(source)
        except Exception as exc:
            raise CommandError(
                "Database reporting tidak dapat dibaca; detail kredensial tidak ditampilkan."
            ) from exc

        frame = raw.copy()
        frame.columns = [str(column).upper() for column in frame.columns]
        identity = source.identity_column.upper()
        latest = source.latest_id_column.upper()
        if identity not in frame.columns:
            errors.append(f"Kolom identitas {identity} tidak ditemukan.")

        raw_rows = int(len(frame))
        blank_identity = None
        duplicate_before = None
        duplicate_after = None
        final_rows = 0
        dataset_fingerprint = ""
        if identity in frame.columns:
            blank_mask = frame[identity].isna() | frame[identity].astype(str).str.strip().eq("")
            blank_identity = int(blank_mask.sum())
            working = frame.loc[~blank_mask].copy()
            duplicate_before = int(working[identity].duplicated(keep=False).sum())
            sort_columns = [name for name in (identity, latest) if name and name in working.columns]
            if latest and latest not in working.columns:
                errors.append(f"Kolom latest ID {latest} tidak ditemukan.")
            if sort_columns:
                working = working.sort_values(sort_columns, kind="stable")
            working = working.drop_duplicates(subset=[identity], keep="last")
            if source.valid_column and source.valid_value:
                valid_column = source.valid_column.upper()
                if valid_column not in working.columns:
                    errors.append(f"Kolom validasi {valid_column} tidak ditemukan.")
                else:
                    working = working[
                        working[valid_column].astype(str).eq(source.valid_value)
                    ]
            duplicate_after = int(working[identity].duplicated(keep=False).sum())
            final_rows = int(len(working))
            if blank_identity:
                errors.append("Dataset memiliki key responden kosong.")
            if duplicate_after:
                errors.append("Key responden tetap duplikat setelah deduplikasi.")
            if not errors:
                dataset_fingerprint = fingerprint_dataset(working, identity, latest)

        metadata_variables = payload.get("variables", {}) if isinstance(payload, dict) else {}
        missing_metadata = sorted(set(metadata_variables) - set(frame.columns))
        if missing_metadata:
            errors.append(
                f"{len(missing_metadata)} variabel metadata tidak tersedia pada tabel reporting."
            )
        if source.target_n is not None and final_rows != source.target_n:
            warnings.append(
                f"Kasus final {final_rows} belum sama dengan target {source.target_n}."
            )

        report = {
            "survey_code": survey.code,
            "database_alias": source.connection_alias,
            "table": source.table_name,
            "raw_rows": raw_rows,
            "final_rows": final_rows,
            "target_n": source.target_n,
            "blank_identity": blank_identity,
            "duplicate_before": duplicate_before,
            "duplicate_after": duplicate_after,
            "metadata_version": metadata.version if metadata else None,
            "metadata_sha256": metadata.sha256 if metadata else None,
            "metadata_variables": len(metadata_variables),
            "missing_metadata_count": len(missing_metadata),
            "dataset_fingerprint": dataset_fingerprint,
            "errors": errors,
            "warnings": warnings,
        }
        if metadata is not None:
            report["configuration_signature"] = event_configuration_signature(
                survey,
                source,
                metadata,
            )
        validation_fingerprint = hashlib.sha256(
            json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        passed = not errors

        self.stdout.write(
            "Validasi event: APPLY" if options["apply"] else "Validasi event: PREVIEW"
        )
        self.stdout.write(f"Survey code: {survey.code}")
        self.stdout.write(f"Current status: {survey.status}")
        self.stdout.write(f"Current active: {str(survey.active).lower()}")
        self.stdout.write(f"Raw rows: {raw_rows}")
        self.stdout.write(f"Final rows: {final_rows}")
        self.stdout.write(f"Target n: {source.target_n if source.target_n is not None else '-'}")
        self.stdout.write(f"Blank identity: {blank_identity if blank_identity is not None else '-'}")
        self.stdout.write(f"Duplicate before dedup: {duplicate_before if duplicate_before is not None else '-'}")
        self.stdout.write(f"Duplicate after dedup: {duplicate_after if duplicate_after is not None else '-'}")
        self.stdout.write(f"Metadata version: {report['metadata_version'] or '-'}")
        self.stdout.write(f"Metadata variables: {report['metadata_variables']}")
        self.stdout.write(f"Missing metadata: {report['missing_metadata_count']}")
        self.stdout.write(f"Errors: {len(errors)}")
        self.stdout.write(f"Warnings: {len(warnings)}")
        for message in errors:
            self.stdout.write(f"ERROR: {message}")
        for message in warnings:
            self.stdout.write(f"WARNING: {message}")
        self.stdout.write(f"Validation result: {'PASSED' if passed else 'FAILED'}")
        self.stdout.write(f"Validation fingerprint: {validation_fingerprint}")

        if options["apply"]:
            survey.validation_state = (
                SurveyAccess.ValidationState.PASSED
                if passed
                else SurveyAccess.ValidationState.FAILED
            )
            survey.validated_at = timezone.now()
            survey.validation_fingerprint = validation_fingerprint
            survey.validation_report = report
            survey.save(
                update_fields=(
                    "validation_state",
                    "validated_at",
                    "validation_fingerprint",
                    "validation_report",
                )
            )
            refresh_event_module_readiness(survey)
            self.stdout.write("Validation report: tersimpan")
        else:
            self.stdout.write("Validation report: belum disimpan")

        if not passed:
            raise CommandError("Validasi event gagal; event tidak boleh diaktifkan.")
