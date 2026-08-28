from contextlib import closing
import os
import re

import pandas as pd

from surnasdes26.services.registry import get_survey


SOURCE_COLUMN_ALIASES = {
    "h0-id": "h0_id",
    "level-1-id": "level_1_id",
}
SQL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")


class SurveyDatabaseConfigurationError(RuntimeError):
    pass


def normalize_source_columns(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.rename(columns=SOURCE_COLUMN_ALIASES)


def _mysql_driver():
    try:
        import MySQLdb
        import MySQLdb.cursors
    except ImportError as exc:
        raise RuntimeError("Driver mysqlclient belum terpasang pada environment ini.") from exc
    return MySQLdb


def get_database_config(survey_code: str | None = None) -> dict:
    survey = get_survey(survey_code)
    database = survey["database"]
    prefix = str(database.get("env_prefix", "")).strip().upper()
    if not prefix:
        raise SurveyDatabaseConfigurationError(
            f"env_prefix belum ditentukan untuk survei {survey['code']}."
        )

    def required(suffix: str) -> str:
        key = f"{prefix}_{suffix}"
        value = os.getenv(key, "").strip()
        if not value:
            raise SurveyDatabaseConfigurationError(
                f"Environment variable {key} wajib diisi untuk survei {survey['code']}."
            )
        return value

    table = str(database.get("table", "h0")).strip()
    if not SQL_IDENTIFIER_PATTERN.fullmatch(table):
        raise SurveyDatabaseConfigurationError(f"Nama tabel tidak aman: {table!r}.")

    try:
        port = int(os.getenv(f"{prefix}_PORT", "3306"))
        connect_timeout = int(os.getenv(f"{prefix}_CONNECT_TIMEOUT", "10"))
    except ValueError as exc:
        raise SurveyDatabaseConfigurationError(
            f"PORT/CONNECT_TIMEOUT untuk {prefix} harus berupa angka."
        ) from exc

    return {
        "SURVEY_CODE": survey["code"],
        "NAME": required("NAME"),
        "USER": required("USER"),
        "PASSWORD": required("PASSWORD"),
        "HOST": os.getenv(f"{prefix}_HOST", "127.0.0.1").strip() or "127.0.0.1",
        "PORT": port,
        "TABLE": table,
        "CONNECT_TIMEOUT": connect_timeout,
        "SSL_CA": os.getenv(f"{prefix}_SSL_CA", "").strip(),
    }


def connect_legacy(survey_code: str | None = None):
    mysql = _mysql_driver()
    config = get_database_config(survey_code)
    options = {
        "host": config["HOST"],
        "port": config["PORT"],
        "user": config["USER"],
        "passwd": config["PASSWORD"],
        "db": config["NAME"],
        "charset": "utf8mb4",
        "connect_timeout": config["CONNECT_TIMEOUT"],
    }
    if config["SSL_CA"]:
        options["ssl"] = {"ca": config["SSL_CA"]}
    return mysql.connect(
        **options,
    )


def count_h0(survey_code: str | None = None) -> int:
    config = get_database_config(survey_code)
    with closing(connect_legacy(config["SURVEY_CODE"])) as connection, closing(
        connection.cursor()
    ) as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM `{config['TABLE']}`")
        return int(cursor.fetchone()[0])


def read_h0(survey_code: str | None = None) -> pd.DataFrame:
    mysql = _mysql_driver()
    config = get_database_config(survey_code)
    with closing(connect_legacy(config["SURVEY_CODE"])) as connection, closing(
        connection.cursor(mysql.cursors.DictCursor)
    ) as cursor:
        cursor.execute(f"SELECT * FROM `{config['TABLE']}`")
        return normalize_source_columns(pd.DataFrame.from_records(cursor.fetchall()))
