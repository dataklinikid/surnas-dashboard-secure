from pathlib import Path

import pandas as pd
from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError

from surnasdes26.models import H0
from surnasdes26.services.legacy_db import read_h0
from surnasdes26.services.registry import get_survey


DEMO_PATH = Path(__file__).resolve().parents[1] / "data" / "demo.csv"


class DatasetUnavailable(RuntimeError):
    pass


def _load_raw(survey_code: str | None = None) -> pd.DataFrame:
    survey = get_survey(survey_code)
    if settings.SURNAS_DEMO_MODE:
        return pd.read_csv(DEMO_PATH)
    if survey["database"].get("legacy_source", True):
        try:
            return read_h0(survey["code"])
        except Exception as exc:
            raise DatasetUnavailable(
                f"Database reporting survei {survey['code']} tidak dapat diakses."
            ) from exc
    try:
        records = H0.objects.using(survey["database"]["alias"]).all().values()
        return pd.DataFrame.from_records(records)
    except DatabaseError as exc:
        raise DatasetUnavailable("Database reporting survei tidak dapat diakses.") from exc


def prepare_dataset(raw: pd.DataFrame, survey_code: str | None = None) -> pd.DataFrame:
    survey = get_survey(survey_code)
    dataset_config = survey["dataset"]
    identity_column = dataset_config["identity_column"]
    latest_id_column = dataset_config["latest_id_column"]

    df = raw.copy()
    df.columns = [str(column).upper() for column in df.columns]

    if identity_column not in df.columns:
        raise DatasetUnavailable(f"Kolom identitas kuesioner {identity_column} tidak ditemukan.")

    df = df.dropna(subset=[identity_column])
    sort_columns = [column for column in (identity_column, latest_id_column) if column in df.columns]
    if sort_columns:
        df = df.sort_values(sort_columns, kind="stable")
    df = df.drop_duplicates(subset=[identity_column], keep="last")

    valid_column = settings.SURNAS_VALID_COLUMN
    valid_value = settings.SURNAS_VALID_VALUE
    if valid_column and valid_value:
        if valid_column not in df.columns:
            raise DatasetUnavailable(f"Kolom filter validasi {valid_column} tidak ditemukan.")
        df = df[df[valid_column].astype(str).eq(valid_value)]

    return df.reset_index(drop=True)


def get_dataset(force_refresh: bool = False, survey_code: str | None = None) -> pd.DataFrame:
    survey = get_survey(survey_code)
    cache_key = f"survey:{survey['code']}:dataset:v1"
    if not force_refresh:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached.copy(deep=True)

    prepared = prepare_dataset(_load_raw(survey["code"]), survey["code"])
    cache.set(cache_key, prepared, timeout=settings.SURNAS_CACHE_SECONDS)
    return prepared.copy(deep=True)
