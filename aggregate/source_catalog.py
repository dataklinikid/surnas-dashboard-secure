import re
from contextlib import closing

from surnasdes26.services.legacy_db import (
    connect_database_config,
    get_connection_profile_config,
)


REPORT_DATABASE_PATTERN = re.compile(
    r"^(?:dbcs|csdb)\d+_[a-z0-9_]+_report$",
    re.IGNORECASE,
)


class SourceCatalogError(RuntimeError):
    pass


def suggested_event_code(database_name):
    match = re.match(
        r"^(?:dbcs|csdb)\d+_(?P<event>[a-z0-9_]+)_report$",
        database_name,
        re.IGNORECASE,
    )
    return match.group("event").lower() if match else ""


def suggested_event_name(database_name):
    code = suggested_event_code(database_name)
    return " ".join(
        re.sub(r"(?<=\D)(?=\d)", " ", part).capitalize()
        for part in code.split("_")
        if part
    )


def verified_link_candidate(profile, database_name):
    requested = str(database_name).strip().casefold()
    rows = discover_reporting_databases(profile)
    candidate = next(
        (row for row in rows if row["database_name"].casefold() == requested),
        None,
    )
    if candidate is None:
        raise SourceCatalogError(
            "Database tidak lagi terlihat pada catalog profile. Pindai ulang sumber."
        )
    if not candidate["table_name"]:
        raise SourceCatalogError("Database tidak memiliki tabel h0.")
    if not candidate.get("has_cspro_meta"):
        raise SourceCatalogError("Database tidak memiliki tabel cspro_meta sebagai sumber metadata produksi.")
    if not candidate["has_identity"]:
        raise SourceCatalogError("Tabel h0 tidak memiliki kolom Q_AC.")
    return candidate


def discover_reporting_databases(profile):
    config = get_connection_profile_config(profile)
    try:
        with closing(connect_database_config(config)) as connection, closing(
            connection.cursor()
        ) as cursor:
            cursor.execute("SHOW DATABASES")
            visible = sorted(
                str(row[0])
                for row in cursor.fetchall()
                if row and REPORT_DATABASE_PATTERN.fullmatch(str(row[0]))
            )
            if not visible:
                return []
            placeholders = ", ".join(["%s"] * len(visible))
            cursor.execute(
                f"""
                SELECT TABLE_SCHEMA, TABLE_NAME, COALESCE(TABLE_ROWS, 0)
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA IN ({placeholders})
                  AND LOWER(TABLE_NAME) IN ('h0', 'cspro_meta')
                """,
                tuple(visible),
            )
            tables = {}
            metadata_databases = set()
            for row in cursor.fetchall():
                database_key = str(row[0]).casefold()
                table_name = str(row[1])
                if table_name.casefold() == "h0":
                    tables[database_key] = (table_name, int(row[2] or 0))
                elif table_name.casefold() == "cspro_meta":
                    metadata_databases.add(database_key)
            cursor.execute(
                f"""
                SELECT TABLE_SCHEMA, TABLE_NAME, COUNT(*),
                       COALESCE(SUM(UPPER(COLUMN_NAME) = 'Q_AC'), 0),
                       COALESCE(SUM(UPPER(REPLACE(COLUMN_NAME, '-', '_')) = 'H0_ID'), 0)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA IN ({placeholders}) AND LOWER(TABLE_NAME) = 'h0'
                GROUP BY TABLE_SCHEMA, TABLE_NAME
                """,
                tuple(visible),
            )
            columns_by_database = {
                str(row[0]).casefold(): (int(row[2] or 0), bool(row[3]), bool(row[4]))
                for row in cursor.fetchall()
            }
            rows = []
            for database_name in visible:
                table = tables.get(database_name.casefold())
                table_name = table[0] if table else ""
                estimated_rows = table[1] if table else None
                columns = columns_by_database.get(database_name.casefold(), (0, False, False))
                column_count, has_identity, has_latest_id = columns
                rows.append(
                    {
                        "database_name": database_name,
                        "table_name": table_name,
                        "estimated_rows": estimated_rows,
                        "column_count": column_count,
                        "has_identity": has_identity,
                        "has_latest_id": has_latest_id,
                        "has_cspro_meta": database_name.casefold() in metadata_databases,
                        "suggested_code": suggested_event_code(database_name),
                    }
                )
    except Exception as exc:
        raise SourceCatalogError(
            "Catalog CSWeb tidak dapat dibaca. Periksa tunnel, environment profile, dan hak SHOW DATABASES/information_schema."
        ) from exc
    return rows
