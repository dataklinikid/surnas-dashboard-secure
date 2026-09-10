from decimal import Decimal

from django.db import transaction

from aggregate.event_validation import event_configuration_signature
from aggregate.models import (
    SurveyAccess,
    SurveyWeight,
    SurveyWeightSet,
)
from aggregate.module_readiness import refresh_event_module_readiness


class WeightReuseError(ValueError):
    pass


def compatible_weight_sets(survey):
    fingerprint = survey.validation_report.get("dataset_fingerprint", "")
    final_rows = survey.validation_report.get("final_rows")
    if survey.validation_state != SurveyAccess.ValidationState.PASSED or not fingerprint:
        return SurveyWeightSet.objects.none()
    return (
        SurveyWeightSet.objects.filter(
            is_active=True,
            coverage=Decimal("100.0000"),
            dataset_fingerprint=fingerprint,
            matched_count=final_rows,
            key_column__iexact=survey.data_source.identity_column,
        )
        .exclude(survey=survey)
        .select_related("survey")
        .order_by("survey__name", "version")
    )


def _validate_current_configuration(survey):
    metadata_rows = list(survey.metadata_versions.filter(is_active=True)[:2])
    if len(metadata_rows) != 1:
        raise WeightReuseError("Event harus memiliki tepat satu metadata aktif.")
    stored = survey.validation_report.get("configuration_signature", "")
    current = event_configuration_signature(survey, survey.data_source, metadata_rows[0])
    if not stored or stored != current:
        raise WeightReuseError("Konfigurasi event berubah; jalankan validasi final kembali.")


def reuse_weight_set(*, survey, source_weight_set, version, user):
    if survey.active or survey.validation_state != SurveyAccess.ValidationState.PASSED:
        raise WeightReuseError("Event harus tidak aktif dan sudah lulus validasi final.")
    _validate_current_configuration(survey)
    compatible_ids = compatible_weight_sets(survey).values_list("pk", flat=True)
    if source_weight_set.pk not in compatible_ids:
        raise WeightReuseError("Weight set sumber tidak kompatibel dengan dataset event.")
    expected_rows = int(survey.validation_report.get("final_rows") or 0)
    actual_weight_rows = source_weight_set.weights.count()
    if not expected_rows or actual_weight_rows != expected_rows:
        raise WeightReuseError(
            f"Jumlah baris bobot sumber {actual_weight_rows} tidak sama dengan kasus final {expected_rows}."
        )
    if source_weight_set.source_row_count != expected_rows:
        raise WeightReuseError("Jumlah baris file sumber tidak sama dengan kasus final event.")
    if SurveyWeightSet.objects.filter(survey=survey, version=version).exists():
        raise WeightReuseError("Versi bobot sudah digunakan pada event target.")

    with transaction.atomic():
        locked_survey = SurveyAccess.objects.select_for_update().get(pk=survey.pk)
        locked_source = SurveyWeightSet.objects.select_for_update().get(pk=source_weight_set.pk)
        if not locked_source.is_active:
            raise WeightReuseError("Weight set sumber tidak lagi aktif.")
        locked_fingerprint = locked_survey.validation_report.get("dataset_fingerprint", "")
        locked_rows = int(locked_survey.validation_report.get("final_rows") or 0)
        locked_key = locked_survey.data_source.identity_column
        if (
            locked_source.coverage != Decimal("100.0000")
            or locked_source.dataset_fingerprint != locked_fingerprint
            or locked_source.matched_count != locked_rows
            or locked_source.source_row_count != locked_rows
            or locked_source.key_column.casefold() != locked_key.casefold()
        ):
            raise WeightReuseError("Kompatibilitas weight set berubah; muat ulang halaman.")
        if locked_source.weights.count() != locked_rows:
            raise WeightReuseError("Jumlah detail bobot sumber berubah; proses dihentikan.")
        SurveyWeightSet.objects.filter(survey=locked_survey, is_active=True).update(
            is_active=False
        )
        target = SurveyWeightSet.objects.create(
            survey=locked_survey,
            parent_weight_set=locked_source,
            version=version,
            method=locked_source.method,
            key_column=locked_source.key_column,
            weight_column=locked_source.weight_column,
            file_sha256=locked_source.file_sha256,
            dataset_fingerprint=locked_source.dataset_fingerprint,
            source_row_count=locked_source.source_row_count,
            matched_count=locked_source.matched_count,
            coverage=locked_source.coverage,
            weight_sum=locked_source.weight_sum,
            weight_min=locked_source.weight_min,
            weight_max=locked_source.weight_max,
            weight_mean=locked_source.weight_mean,
            effective_sample_size=locked_source.effective_sample_size,
            is_active=True,
            created_by=user,
        )
        SurveyWeight.objects.bulk_create(
            [
                SurveyWeight(
                    weight_set=target,
                    respondent_key=row.respondent_key,
                    weight=row.weight,
                )
                for row in locked_source.weights.only("respondent_key", "weight").iterator(
                    chunk_size=1000
                )
            ],
            batch_size=1000,
        )

    survey.refresh_from_db()
    refresh_event_module_readiness(survey)
    return target
