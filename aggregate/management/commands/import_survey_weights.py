import hashlib
import re
from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from aggregate.models import SurveyAccess, SurveyWeight, SurveyWeightSet
from aggregate.weighting import (
    MAX_WEIGHT_FILE_BYTES,
    WeightValidationError,
    audit_weight_frame,
    decimal_weight,
)
from surnasdes26.services.dataset import DatasetUnavailable, get_dataset
from surnasdes26.services.registry import SurveyRegistryError, get_survey


class Command(BaseCommand):
    help = "Memvalidasi dan mengimpor satu versi bobot. Default hanya preview."

    def add_arguments(self, parser):
        parser.add_argument("--survey-code", required=True)
        parser.add_argument("--file", required=True)
        parser.add_argument("--weight-version", required=True)
        parser.add_argument("--method", default="offline")
        parser.add_argument("--key-column")
        parser.add_argument("--weight-column", default="WEIGHT")
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        survey_code = options["survey_code"].strip().lower()
        version = options["weight_version"].strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", version):
            raise CommandError(
                "Weight version hanya boleh huruf kecil, angka, underscore, dan tanda hubung."
            )
        source = Path(options["file"]).expanduser().resolve()
        if not source.is_file():
            raise CommandError(f"File bobot tidak ditemukan: {source}.")
        if source.suffix.lower() != ".csv":
            raise CommandError("File bobot wajib berformat CSV.")
        if source.stat().st_size > MAX_WEIGHT_FILE_BYTES:
            raise CommandError("Ukuran file bobot melebihi batas 20 MB.")
        try:
            manifest = get_survey(survey_code)
            key_column = str(options.get("key_column") or manifest["dataset"]["identity_column"]).upper()
            weight_column = options["weight_column"].strip().upper()
            frame = pd.read_csv(source, dtype=str, keep_default_na=False, encoding="utf-8-sig")
            dataset = get_dataset(force_refresh=True, survey_code=survey_code)
            audit = audit_weight_frame(
                dataset,
                frame,
                key_column=key_column,
                weight_column=weight_column,
                version_column=manifest["dataset"].get("latest_id_column"),
            )
        except (OSError, UnicodeError, pd.errors.ParserError, SurveyRegistryError, DatasetUnavailable, WeightValidationError) as exc:
            raise CommandError(str(exc)) from exc

        action = "APPLIED" if options["apply"] else "PREVIEW"
        self.stdout.write(self.style.SUCCESS(f"Import survey weights: {action}"))
        self.stdout.write(f"Survey code: {survey_code}")
        self.stdout.write(f"Version: {version}")
        self.stdout.write(f"Kasus dataset: {audit['dataset_count']}")
        self.stdout.write(f"Baris CSV: {audit['source_row_count']}")
        self.stdout.write(f"Matched: {audit['matched_count']}")
        self.stdout.write(f"Missing: {audit['missing_count']}")
        self.stdout.write(f"Unknown: {audit['unknown_count']}")
        self.stdout.write(f"Duplikat key: {audit['duplicate_key_count']}")
        self.stdout.write(f"Bobot invalid: {audit['blank_weight_count'] + audit['non_numeric_count'] + audit['non_finite_count'] + audit['non_positive_count']}")
        self.stdout.write(f"Coverage: {audit['coverage']:.4f}%")
        self.stdout.write(f"Weight min/max/mean: {audit['weight_min']:.6f} / {audit['weight_max']:.6f} / {audit['weight_mean']:.6f}")
        self.stdout.write(f"Sum weight: {audit['weight_sum']:.6f}")
        self.stdout.write(f"Effective sample size: {audit['effective_sample_size']:.3f}")
        if audit["errors"]:
            for error in audit["errors"]:
                self.stdout.write(self.style.ERROR(f"VALIDATION: {error}"))
            if options["apply"]:
                raise CommandError("Bobot tidak diimpor karena validasi gagal.")
            self.stdout.write("Preview selesai; --apply akan ditolak sampai seluruh validasi lulus.")
            return

        if not options["apply"]:
            self.stdout.write("Validasi lulus. Tambahkan --apply untuk menyimpan versi bobot.")
            return

        try:
            survey = SurveyAccess.objects.get(code=survey_code, active=True)
        except SurveyAccess.DoesNotExist as exc:
            raise CommandError(
                "Survei belum tersedia pada kontrol akses. Jalankan sync_survey_access."
            ) from exc
        if SurveyWeightSet.objects.filter(survey=survey, version=version).exists():
            raise CommandError("Versi bobot sudah tersedia; gunakan nama versi baru.")

        file_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
        with transaction.atomic():
            weight_set = SurveyWeightSet.objects.create(
                survey=survey,
                version=version,
                method=options["method"].strip(),
                key_column=key_column,
                weight_column=weight_column,
                file_sha256=file_sha256,
                dataset_fingerprint=audit["dataset_fingerprint"],
                source_row_count=audit["source_row_count"],
                matched_count=audit["matched_count"],
                coverage=decimal_weight(audit["coverage"]),
                weight_sum=decimal_weight(audit["weight_sum"]),
                weight_min=decimal_weight(audit["weight_min"]),
                weight_max=decimal_weight(audit["weight_max"]),
                weight_mean=decimal_weight(audit["weight_mean"]),
                effective_sample_size=decimal_weight(audit["effective_sample_size"]),
                is_active=False,
            )
            SurveyWeight.objects.bulk_create(
                [
                    SurveyWeight(
                        weight_set=weight_set,
                        respondent_key=row.respondent_key,
                        weight=decimal_weight(row.weight),
                    )
                    for row in audit["normalized"].itertuples(index=False)
                ],
                batch_size=1000,
            )
        self.stdout.write(f"Weight set ID: {weight_set.pk}")
        self.stdout.write("Status: tersimpan, belum aktif")
