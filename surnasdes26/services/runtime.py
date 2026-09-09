import copy
import hashlib
import json

from django.conf import settings
from django.db import DatabaseError

from surnasdes26.services.registry import (
    SurveyRegistryError,
    active_survey_code,
    enabled_surveys,
    get_survey,
    load_registry,
)


def metadata_sha256(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _postgres_manifest(code: str, fallback: dict | None) -> dict | None:
    if not settings.SURVEY_CONTROL_PLANE_ENABLED:
        return None
    from aggregate.models import SurveyAccess, SurveyDataSource

    try:
        survey = (
            SurveyAccess.objects.select_related("program", "region")
            .filter(code=code, active=True, status=SurveyAccess.Status.ACTIVE)
            .first()
        )
        if survey is None:
            return None
        try:
            source = survey.data_source
        except SurveyDataSource.DoesNotExist:
            return None
        if not source.active:
            return None
        metadata_rows = list(survey.metadata_versions.filter(is_active=True)[:2])
    except DatabaseError:
        return None

    if len(metadata_rows) != 1:
        return None
    metadata = metadata_rows[0]
    payload = metadata.payload
    if not isinstance(payload, dict) or not isinstance(payload.get("variables"), dict):
        return None
    if metadata_sha256(payload) != metadata.sha256:
        return None
    metadata_code = str(payload.get("survey", {}).get("code", "")).strip().lower()
    if metadata_code and metadata_code != survey.code:
        return None

    fallback = fallback or {}
    configuration_fingerprint = hashlib.sha256(
        f"{source.pk}:{source.updated_at.isoformat()}:{metadata.sha256}".encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 2,
        "code": survey.code,
        "name": survey.name,
        "enabled": True,
        "database": {
            "alias": source.connection_alias,
            "env_prefix": source.environment_prefix,
            "name": source.database_name,
            "table": source.table_name,
            "legacy_source": source.engine == SurveyDataSource.Engine.MARIADB,
        },
        "metadata": {
            "payload": copy.deepcopy(payload),
            "version": metadata.version,
            "sha256": metadata.sha256,
            "source_name": metadata.source_name,
        },
        "dataset": {
            "identity_column": source.identity_column.upper(),
            "latest_id_column": source.latest_id_column.upper(),
            "target_n": source.target_n,
            "valid_column": source.valid_column.upper(),
            "valid_value": source.valid_value,
        },
        "privacy": copy.deepcopy(
            survey.privacy_config
            or fallback.get("privacy", {"aggregate_only": True})
        ),
        "dashboard": copy.deepcopy(
            survey.dashboard_config
            or fallback.get("dashboard", {})
        ),
        "program": {
            "code": survey.program.code,
            "name": survey.program.name,
        } if survey.program else None,
        "region": {
            "code": survey.region.code,
            "name": survey.region.name,
            "level": survey.region.level,
        } if survey.region else None,
        "period_start": survey.period_start,
        "period_end": survey.period_end,
        "configuration_source": "postgresql",
        "configuration_fingerprint": configuration_fingerprint,
        "source_path": fallback.get("source_path"),
    }


def resolve_survey(code: str | None = None) -> dict:
    selected = str(code or active_survey_code()).strip().lower()
    fallback = load_registry().get(selected)
    postgres = _postgres_manifest(selected, fallback)
    if postgres is not None:
        return postgres
    manifest = get_survey(selected)
    resolved = dict(manifest)
    resolved["configuration_source"] = "json"
    resolved["configuration_fingerprint"] = hashlib.sha256(
        str(manifest["source_path"]).encode("utf-8")
    ).hexdigest()
    return resolved


def enabled_runtime_surveys() -> list[dict]:
    from aggregate.models import SurveyAccess

    codes = {manifest["code"] for manifest in enabled_surveys()}
    try:
        if not settings.SURVEY_CONTROL_PLANE_ENABLED:
            return sorted(
                (resolve_survey(code) for code in codes),
                key=lambda item: (item["name"].casefold(), item["code"]),
            )
        codes.update(
            SurveyAccess.objects.filter(
                active=True,
                status=SurveyAccess.Status.ACTIVE,
            ).values_list("code", flat=True)
        )
    except DatabaseError:
        pass

    manifests = []
    for code in sorted(codes):
        try:
            manifests.append(resolve_survey(code))
        except SurveyRegistryError:
            continue
    return sorted(manifests, key=lambda item: (item["name"].casefold(), item["code"]))
