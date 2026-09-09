import copy
import hashlib
import json
from contextlib import closing

from django.utils import timezone

from surnasdes26.services.legacy_db import (
    SOURCE_COLUMN_ALIASES,
    _mysql_driver,
    connect_database_config,
    get_data_source_config,
)
from surnasdes26.services.cspro_metadata import (
    MetadataParseError,
    build_canonical_metadata_from_content,
)
from surnasdes26.services.runtime import metadata_sha256, resolve_survey


class MetadataOnboardingError(ValueError):
    pass


def monitoring_dashboard_config(payload, template_event=None):
    variables = {
        str(name).strip().upper(): definition
        for name, definition in payload.get("variables", {}).items()
    }
    dashboard = {}
    if template_event is not None:
        dashboard = copy.deepcopy(resolve_survey(template_event.code).get("dashboard", {}))
    elif isinstance(payload.get("dashboard"), dict):
        dashboard = copy.deepcopy(payload["dashboard"])

    variable = str(dashboard.get("monitoring_group_variable", "")).strip().upper()
    if not variable and "Q_F" in variables:
        variable = "Q_F"
    if not variable:
        return {}
    if variable not in variables:
        raise MetadataOnboardingError(
            f"Variabel monitoring {variable} tidak tersedia pada metadata."
        )
    definition = variables.get(variable, {})
    default_label = definition.get("label", variable) if isinstance(definition, dict) else variable
    dashboard["monitoring_group_variable"] = variable
    dashboard["monitoring_group_label"] = str(
        dashboard.get("monitoring_group_label") or default_label
    ).strip()
    return dashboard


def _validate_metadata_contract(payload, survey):
    if not isinstance(payload, dict):
        raise MetadataOnboardingError("Metadata harus berupa JSON object.")
    variables = payload.get("variables")
    if not isinstance(variables, dict) or not variables:
        raise MetadataOnboardingError("Metadata harus memiliki object variables yang tidak kosong.")
    survey_payload = payload.get("survey")
    if not isinstance(survey_payload, dict):
        raise MetadataOnboardingError("Metadata harus memiliki object survey.")
    if str(survey_payload.get("code", "")).strip().lower() != survey.code:
        raise MetadataOnboardingError("Kode event pada metadata tidak cocok dengan draft event.")
    source_table = str(survey_payload.get("source_table", "")).strip()
    if source_table.casefold() != survey.data_source.table_name.casefold():
        raise MetadataOnboardingError("Tabel sumber pada metadata tidak cocok dengan data source event.")
    aggregate_only = payload.get("privacy", {}).get(
        "aggregate_only",
        survey_payload.get("aggregate_only"),
    )
    if aggregate_only is not True:
        raise MetadataOnboardingError("Metadata harus menggunakan aggregate_only=true.")
    if payload.get("build_report", {}).get("contains_respondent_rows") is not False:
        raise MetadataOnboardingError("Metadata harus menggunakan contains_respondent_rows=false.")


def _inspection_report(
    *,
    survey,
    payload,
    raw_rows,
    available_columns,
    read_only_queries,
    metadata_source=None,
):
    identity = survey.data_source.identity_column.upper()
    latest = survey.data_source.latest_id_column.upper()
    valid_column = survey.data_source.valid_column.upper()
    metadata_columns = required_metadata_columns(payload)
    required_columns = set(metadata_columns)
    required_columns.add(identity)
    if latest:
        required_columns.add(latest)
    if valid_column:
        required_columns.add(valid_column)
    missing = sorted(required_columns - available_columns)
    errors = []
    warnings = []
    if missing:
        errors.append(f"{len(missing)} kolom wajib tidak tersedia pada tabel reporting.")
    if survey.data_source.target_n is not None and raw_rows != survey.data_source.target_n:
        warnings.append(
            f"Baris mentah {raw_rows} belum sama dengan target {survey.data_source.target_n}; pemeriksaan final dilakukan setelah deduplikasi."
        )

    report = {
        "checked_at": timezone.now().isoformat(),
        "survey_code": survey.code,
        "connection_profile": survey.data_source.connection_profile.code
        if survey.data_source.connection_profile
        else survey.data_source.connection_alias,
        "environment_prefix": survey.data_source.environment_prefix,
        "database_name": survey.data_source.database_name,
        "table_name": survey.data_source.table_name,
        "raw_rows": raw_rows,
        "target_n": survey.data_source.target_n,
        "available_column_count": len(available_columns),
        "metadata_column_count": len(metadata_columns),
        "required_column_count": len(required_columns),
        "missing_column_count": len(missing),
        "missing_columns": missing,
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
        "read_only_queries": read_only_queries,
    }
    if metadata_source:
        report["metadata_source"] = metadata_source
    return report


def _database_metadata_candidate(survey):
    source = survey.data_source
    config = get_data_source_config(source)
    mysql = _mysql_driver()
    try:
        with closing(connect_database_config(config)) as connection, closing(
            connection.cursor(mysql.cursors.DictCursor)
        ) as cursor:
            cursor.execute(
                """
                SELECT id, cspro_version, dictionary, source_modified_time,
                       created_time, modified_time
                FROM cspro_meta
                ORDER BY modified_time DESC, id DESC
                LIMIT 1
                """
            )
            metadata_row = cursor.fetchone()
            cursor.execute(
                """
                SELECT COLUMN_NAME, ORDINAL_POSITION, COLUMN_TYPE, IS_NULLABLE,
                       COLUMN_KEY, EXTRA, CHARACTER_SET_NAME, COLLATION_NAME,
                       COLUMN_COMMENT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
                """,
                (config["NAME"], config["TABLE"]),
            )
            columns = [dict(row) for row in cursor.fetchall()]
            cursor.execute(f"SELECT COUNT(*) AS raw_rows FROM `{config['TABLE']}`")
            raw_rows = int(cursor.fetchone()["raw_rows"])
    except Exception as exc:
        raise MetadataOnboardingError(
            "Metadata produksi tidak dapat dibaca. Periksa profil koneksi, cspro_meta, schema h0, dan hak SELECT."
        ) from exc

    if not metadata_row or not metadata_row.get("dictionary"):
        raise MetadataOnboardingError("Dictionary produksi pada cspro_meta tidak ditemukan.")
    if not columns:
        raise MetadataOnboardingError("Schema tabel h0 tidak ditemukan pada database reporting.")

    dictionary_text = str(metadata_row["dictionary"])
    schema = {
        "table": config["TABLE"],
        "column_count": len(columns),
        "columns": columns,
    }
    try:
        payload = build_canonical_metadata_from_content(
            dictionary_text,
            schema,
            survey.code,
            survey.name,
        )
    except MetadataParseError as exc:
        raise MetadataOnboardingError(f"Dictionary produksi tidak dapat diparsing: {exc}") from exc

    available_columns = {
        SOURCE_COLUMN_ALIASES.get(
            str(column["COLUMN_NAME"]).strip().lower(),
            str(column["COLUMN_NAME"]).strip(),
        ).upper()
        for column in columns
    }
    source_signature = {
        "kind": "database_cspro_meta",
        "row_id": metadata_row["id"],
        "cspro_version": str(metadata_row.get("cspro_version", "")),
        "source_modified_time": str(metadata_row.get("source_modified_time", "")),
        "metadata_modified_time": str(metadata_row.get("modified_time", "")),
        "dictionary_length": len(dictionary_text),
        "dictionary_sha256": hashlib.sha256(dictionary_text.encode("utf-8")).hexdigest(),
        "contains_respondent_rows": False,
    }
    report = _inspection_report(
        survey=survey,
        payload=payload,
        raw_rows=raw_rows,
        available_columns=available_columns,
        read_only_queries=3,
        metadata_source=source_signature,
    )
    return payload, report, source_signature


def _metadata_identity(payload, survey):
    questionnaire_key = str(payload.get("survey", {}).get("dictionary_name", "")).strip().upper()
    if not questionnaire_key:
        raise MetadataOnboardingError("Dictionary produksi tidak memiliki identitas questionnaire.")
    source_database = survey.data_source.database_name.strip().casefold()
    from aggregate.models import SurveyMetadataVersion

    owner = (
        SurveyMetadataVersion.objects.filter(
            questionnaire_key=questionnaire_key,
            is_active=True,
        )
        .exclude(survey=survey)
        .select_related("survey")
        .first()
    )
    if owner:
        raise MetadataOnboardingError(
            f"Identitas kuesioner sudah digunakan oleh event lain: {owner.survey.code}."
        )
    return questionnaire_key, source_database


def prepare_metadata_candidate(
    *,
    survey,
    source_mode="database",
    template_event=None,
    uploaded_file=None,
):
    report = None
    source_signature = None
    if source_mode == "database":
        payload, report, source_signature = _database_metadata_candidate(survey)
        source_name = (
            f"database:{survey.data_source.database_name}.cspro_meta:"
            f"{source_signature['row_id']}"
        )
        schema_version = int(payload.get("metadata_schema_version", 1))
    elif source_mode == "template":
        if template_event is None:
            raise MetadataOnboardingError("Template event wajib dipilih.")
        rows = list(template_event.metadata_versions.filter(is_active=True)[:2])
        if len(rows) != 1:
            raise MetadataOnboardingError("Template event harus memiliki tepat satu metadata aktif.")
        template = rows[0]
        payload = copy.deepcopy(template.payload)
        payload.setdefault("survey", {})["code"] = survey.code
        payload["survey"]["name"] = survey.name
        payload["survey"]["source_table"] = survey.data_source.table_name
        source_name = f"template:{template_event.code}:{template.version}"
        schema_version = template.metadata_schema_version
    elif source_mode == "upload":
        if uploaded_file is None:
            raise MetadataOnboardingError("File metadata JSON wajib dipilih.")
        try:
            payload = json.loads(uploaded_file.read().decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MetadataOnboardingError("File metadata bukan JSON UTF-8 yang valid.") from exc
        source_name = uploaded_file.name
        try:
            schema_version = int(payload.get("metadata_schema_version", 1))
        except (TypeError, ValueError) as exc:
            raise MetadataOnboardingError("metadata_schema_version harus berupa angka.") from exc
    else:
        raise MetadataOnboardingError("Sumber metadata tidak valid.")

    _validate_metadata_contract(payload, survey)
    questionnaire_key, source_database = _metadata_identity(payload, survey)
    return {
        "payload": payload,
        "sha256": metadata_sha256(payload),
        "source_name": source_name,
        "metadata_schema_version": schema_version,
        "questionnaire_key": questionnaire_key,
        "source_database": source_database,
        "onboarding_report": report,
        "source_signature": source_signature,
        "dashboard_config": monitoring_dashboard_config(
            payload,
            template_event=template_event if source_mode == "template" else None,
        ),
    }


def required_metadata_columns(payload):
    columns = {str(name).strip().upper() for name in payload.get("variables", {})}
    for group in payload.get("multiple_answer_groups", {}).values():
        if not isinstance(group, dict):
            continue
        if group.get("storage") == "compact_codes":
            source_column = str(group.get("source_column", "")).strip().upper()
            if source_column:
                columns.add(source_column)
            continue
        for option in group.get("options", []):
            if isinstance(option, dict) and option.get("column"):
                columns.add(str(option["column"]).strip().upper())
    return columns


def inspect_metadata_source(*, survey, payload):
    source = survey.data_source
    config = get_data_source_config(source)
    try:
        with closing(connect_database_config(config)) as connection, closing(
            connection.cursor()
        ) as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM `{config['TABLE']}`")
            raw_rows = int(cursor.fetchone()[0])
            cursor.execute(f"SELECT * FROM `{config['TABLE']}` LIMIT 0")
            available_columns = {
                SOURCE_COLUMN_ALIASES.get(
                    str(description[0]).strip().lower(),
                    str(description[0]).strip(),
                ).upper()
                for description in cursor.description or ()
            }
    except Exception as exc:
        raise MetadataOnboardingError(
            "Database reporting tidak dapat diperiksa. Periksa profil koneksi, nama database, tabel, dan hak SELECT."
        ) from exc

    return _inspection_report(
        survey=survey,
        payload=payload,
        raw_rows=raw_rows,
        available_columns=available_columns,
        read_only_queries=2,
    )
