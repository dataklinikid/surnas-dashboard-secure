import hashlib
import math
from decimal import Decimal

import pandas as pd


MAX_WEIGHT_FILE_BYTES = 20 * 1024 * 1024
INTERNAL_WEIGHT_COLUMN = "__SURVEY_WEIGHT__"


class WeightValidationError(ValueError):
    pass


class ActiveWeightUnavailable(WeightValidationError):
    pass


def canonical_respondent_key(value) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def fingerprint_keys(keys) -> str:
    payload = "\n".join(sorted(keys)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fingerprint_dataset(
    dataset: pd.DataFrame,
    key_column: str,
    version_column: str | None = None,
) -> str:
    column_map = {str(column).strip().upper(): column for column in dataset.columns}
    key_name = key_column.strip().upper()
    if key_name not in column_map:
        raise WeightValidationError(f"Kolom key dataset tidak tersedia: {key_name}.")
    keys = dataset[column_map[key_name]].map(canonical_respondent_key)
    version_name = str(version_column or "").strip().upper()
    if version_name and version_name in column_map:
        versions = dataset[column_map[version_name]].map(canonical_respondent_key)
        records = [
            f"{key}\t{version}"
            for key, version in zip(keys, versions)
            if key
        ]
        return fingerprint_keys(records)
    return fingerprint_keys(key for key in keys if key)


def audit_weight_frame(
    dataset: pd.DataFrame,
    weight_frame: pd.DataFrame,
    *,
    key_column: str,
    weight_column: str,
    version_column: str | None = None,
) -> dict:
    key_column = key_column.strip().upper()
    weight_column = weight_column.strip().upper()
    dataset_columns = {str(column).strip().upper(): column for column in dataset.columns}
    if key_column not in dataset_columns:
        raise WeightValidationError(f"Kolom key dataset tidak tersedia: {key_column}.")

    frame = weight_frame.copy()
    frame.columns = [str(column).strip().upper() for column in frame.columns]
    missing_columns = [name for name in (key_column, weight_column) if name not in frame.columns]
    if missing_columns:
        raise WeightValidationError(
            f"Kolom CSV tidak tersedia: {', '.join(missing_columns)}."
        )

    dataset_keys = dataset[dataset_columns[key_column]].map(canonical_respondent_key)
    blank_dataset_keys = int(dataset_keys.eq("").sum())
    duplicate_dataset_keys = int(dataset_keys.duplicated(keep=False).sum())
    csv_keys = frame[key_column].map(canonical_respondent_key)
    blank_csv_keys = int(csv_keys.eq("").sum())
    duplicate_csv_keys = int(csv_keys[csv_keys.ne("")].duplicated(keep=False).sum())

    raw_weights = frame[weight_column].astype(str).str.strip()
    numeric_weights = pd.to_numeric(raw_weights, errors="coerce")
    non_numeric_weights = int((raw_weights.ne("") & numeric_weights.isna()).sum())
    blank_weights = int(raw_weights.eq("").sum())
    non_finite_weights = int(
        numeric_weights.notna().sum()
        - numeric_weights[numeric_weights.notna()].map(math.isfinite).sum()
    )
    non_positive_weights = int((numeric_weights.notna() & numeric_weights.le(0)).sum())

    dataset_key_set = set(dataset_keys[dataset_keys.ne("")])
    csv_key_set = set(csv_keys[csv_keys.ne("")])
    matched_keys = dataset_key_set & csv_key_set
    missing_keys = dataset_key_set - csv_key_set
    unknown_keys = csv_key_set - dataset_key_set
    coverage = (len(matched_keys) / len(dataset_key_set) * 100) if dataset_key_set else 0.0

    valid_weight_mask = (
        csv_keys.ne("")
        & numeric_weights.notna()
        & numeric_weights.gt(0)
        & numeric_weights.map(lambda value: math.isfinite(value) if pd.notna(value) else False)
    )
    valid_weights = numeric_weights[valid_weight_mask]
    weight_sum = float(valid_weights.sum()) if not valid_weights.empty else 0.0
    squared_sum = float(valid_weights.pow(2).sum()) if not valid_weights.empty else 0.0
    effective_sample_size = (weight_sum**2 / squared_sum) if squared_sum else 0.0

    errors = []
    checks = (
        (blank_dataset_keys, "Dataset memiliki key kosong."),
        (duplicate_dataset_keys, "Dataset memiliki key duplikat setelah normalisasi."),
        (blank_csv_keys, "CSV memiliki key kosong."),
        (duplicate_csv_keys, "CSV memiliki key duplikat."),
        (blank_weights, "CSV memiliki bobot kosong."),
        (non_numeric_weights, "CSV memiliki bobot tidak numerik."),
        (non_finite_weights, "CSV memiliki bobot tidak finite."),
        (non_positive_weights, "CSV memiliki bobot nol atau negatif."),
        (len(missing_keys), "Sebagian kasus dataset belum memiliki bobot."),
        (len(unknown_keys), "CSV memiliki key yang tidak ditemukan pada dataset."),
    )
    errors.extend(message for count, message in checks if count)
    if coverage != 100.0:
        errors.append("Coverage bobot harus tepat 100%.")

    normalized = pd.DataFrame(
        {
            "respondent_key": csv_keys,
            "weight": numeric_weights,
        }
    )
    return {
        "normalized": normalized,
        "dataset_count": len(dataset_key_set),
        "source_row_count": int(len(frame)),
        "matched_count": len(matched_keys),
        "missing_count": len(missing_keys),
        "unknown_count": len(unknown_keys),
        "blank_key_count": blank_csv_keys,
        "duplicate_key_count": duplicate_csv_keys,
        "blank_weight_count": blank_weights,
        "non_numeric_count": non_numeric_weights,
        "non_finite_count": non_finite_weights,
        "non_positive_count": non_positive_weights,
        "coverage": coverage,
        "weight_sum": weight_sum,
        "weight_min": float(valid_weights.min()) if not valid_weights.empty else 0.0,
        "weight_max": float(valid_weights.max()) if not valid_weights.empty else 0.0,
        "weight_mean": float(valid_weights.mean()) if not valid_weights.empty else 0.0,
        "effective_sample_size": effective_sample_size,
        "dataset_fingerprint": fingerprint_dataset(dataset, key_column, version_column),
        "errors": errors,
    }


def decimal_weight(value) -> Decimal:
    return Decimal(str(value))


def active_weight_status(dataset: pd.DataFrame, survey_code: str) -> dict:
    from aggregate.models import SurveyWeightSet
    from surnasdes26.services.registry import get_survey

    manifest = get_survey(survey_code)
    weight_set = (
        SurveyWeightSet.objects.select_related("survey")
        .filter(survey__code=survey_code, is_active=True)
        .first()
    )
    if weight_set is None:
        return {
            "available": False,
            "valid": False,
            "mode": "unweighted",
            "message": "Belum ada versi bobot aktif untuk survei ini.",
        }

    key_column = weight_set.key_column.upper()
    if key_column not in dataset.columns:
        return {
            "available": True,
            "valid": False,
            "mode": "unweighted",
            "version": weight_set.version,
            "message": f"Kolom key bobot tidak tersedia: {key_column}.",
        }
    dataset_keys = {
        canonical_respondent_key(value)
        for value in dataset[key_column]
        if canonical_respondent_key(value)
    }
    weight_keys = set(weight_set.weights.values_list("respondent_key", flat=True))
    missing_count = len(dataset_keys - weight_keys)
    unknown_count = len(weight_keys - dataset_keys)
    fingerprint_match = fingerprint_dataset(
        dataset,
        key_column,
        manifest["dataset"].get("latest_id_column"),
    ) == weight_set.dataset_fingerprint
    valid = not missing_count and not unknown_count and fingerprint_match
    return {
        "available": True,
        "valid": valid,
        "mode": "unweighted",
        "version": weight_set.version,
        "method": weight_set.method,
        "coverage": float(weight_set.coverage),
        "weight_sum": float(weight_set.weight_sum),
        "effective_sample_size": float(weight_set.effective_sample_size),
        "missing_count": missing_count,
        "unknown_count": unknown_count,
        "fingerprint_match": fingerprint_match,
        "message": (
            "Bobot aktif siap digunakan."
            if valid
            else "Bobot aktif tidak sinkron dengan dataset terbaru."
        ),
        "weight_set": weight_set,
    }


def resolve_weighting(
    dataset: pd.DataFrame,
    survey_code: str,
    requested_mode: str,
) -> tuple[pd.DataFrame, str | None, dict]:
    mode = str(requested_mode or "unweighted").strip().lower()
    if mode not in {"unweighted", "weighted"}:
        raise ActiveWeightUnavailable("Mode pembobotan tidak valid.")
    status = active_weight_status(dataset, survey_code)
    status["mode"] = mode
    if mode == "unweighted":
        return dataset, None, status
    if not status.get("available") or not status.get("valid"):
        raise ActiveWeightUnavailable(status.get("message", "Bobot aktif tidak tersedia."))

    weight_set = status["weight_set"]
    key_column = weight_set.key_column.upper()
    weight_map = {
        key: float(weight)
        for key, weight in weight_set.weights.values_list("respondent_key", "weight")
    }
    weighted = dataset.copy()
    weighted[INTERNAL_WEIGHT_COLUMN] = weighted[key_column].map(
        lambda value: weight_map.get(canonical_respondent_key(value))
    )
    if weighted[INTERNAL_WEIGHT_COLUMN].isna().any():
        raise ActiveWeightUnavailable("Join bobot menghasilkan kasus tanpa bobot.")
    return weighted, INTERNAL_WEIGHT_COLUMN, status
