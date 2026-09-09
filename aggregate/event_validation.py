import hashlib
import json

from surnasdes26.services.runtime import metadata_sha256


def event_configuration_signature(survey, source, metadata) -> str:
    payload = {
        "survey": {
            "code": survey.code,
            "name": survey.name,
            "event_type_id": survey.event_type_id,
            "program_id": survey.program_id,
            "region_id": survey.region_id,
            "period_start": survey.period_start.isoformat() if survey.period_start else None,
            "period_end": survey.period_end.isoformat() if survey.period_end else None,
            "dashboard_config": survey.dashboard_config,
            "privacy_config": survey.privacy_config,
        },
        "modules": [
            {
                "code": assignment.module.code,
                "enabled": assignment.enabled,
                "config": assignment.config,
            }
            for assignment in survey.event_modules.select_related("module").order_by(
                "module__code"
            )
        ],
        "data_source": {
            "connection_profile_id": source.connection_profile_id,
            "engine": source.engine,
            "connection_alias": source.connection_alias,
            "environment_prefix": source.environment_prefix,
            "database_name": source.database_name,
            "table_name": source.table_name,
            "identity_column": source.identity_column,
            "latest_id_column": source.latest_id_column,
            "valid_column": source.valid_column,
            "valid_value": source.valid_value,
            "target_n": source.target_n,
            "active": source.active,
        },
        "metadata": {
            "version": metadata.version,
            "metadata_schema_version": metadata.metadata_schema_version,
            "questionnaire_key": metadata.questionnaire_key,
            "source_database": metadata.source_database,
            "stored_sha256": metadata.sha256,
            "calculated_sha256": metadata_sha256(metadata.payload),
            "is_active": metadata.is_active,
        },
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
