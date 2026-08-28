import json
import re
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


SURVEY_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
DATABASE_ALIAS_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")


class SurveyRegistryError(ImproperlyConfigured):
    pass


def _require_object(payload: dict, key: str, source: Path) -> dict:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise SurveyRegistryError(f"{source}: object '{key}' wajib tersedia.")
    return value


def _safe_project_path(relative_path: str, source: Path) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise SurveyRegistryError(f"{source}: metadata.path harus relatif terhadap root project.")
    resolved = (settings.BASE_DIR / candidate).resolve()
    try:
        resolved.relative_to(settings.BASE_DIR.resolve())
    except ValueError as exc:
        raise SurveyRegistryError(f"{source}: metadata.path keluar dari root project.") from exc
    return resolved


def _validate_manifest(payload: dict, source: Path) -> dict:
    if payload.get("schema_version") != 1:
        raise SurveyRegistryError(f"{source}: schema_version yang didukung hanya 1.")

    code = str(payload.get("code", "")).strip().lower()
    if not SURVEY_CODE_PATTERN.fullmatch(code):
        raise SurveyRegistryError(f"{source}: survey code tidak valid: {code!r}.")
    if source.stem != code:
        raise SurveyRegistryError(f"{source}: nama file harus sama dengan survey code '{code}'.")

    name = str(payload.get("name", "")).strip()
    if not name:
        raise SurveyRegistryError(f"{source}: name wajib diisi.")

    database = _require_object(payload, "database", source)
    alias = str(database.get("alias", "")).strip()
    if not DATABASE_ALIAS_PATTERN.fullmatch(alias):
        raise SurveyRegistryError(f"{source}: database.alias tidak valid: {alias!r}.")
    table = str(database.get("table", "")).strip()
    if not table:
        raise SurveyRegistryError(f"{source}: database.table wajib diisi.")

    metadata = _require_object(payload, "metadata", source)
    metadata_path = _safe_project_path(str(metadata.get("path", "")).strip(), source)
    if not metadata_path.is_file():
        raise SurveyRegistryError(f"{source}: file metadata tidak ditemukan: {metadata_path}.")

    dataset = _require_object(payload, "dataset", source)
    identity_column = str(dataset.get("identity_column", "")).strip().upper()
    if not identity_column:
        raise SurveyRegistryError(f"{source}: dataset.identity_column wajib diisi.")
    latest_id_column = str(dataset.get("latest_id_column", "")).strip().upper()

    normalized = dict(payload)
    normalized["code"] = code
    normalized["name"] = name
    normalized["enabled"] = bool(payload.get("enabled", True))
    normalized["database"] = {
        **database,
        "alias": alias,
        "table": table,
        "env_prefix": str(database.get("env_prefix", "")).strip().upper(),
        "legacy_source": bool(database.get("legacy_source", False)),
    }
    normalized["metadata"] = {**metadata, "resolved_path": metadata_path}
    normalized["dataset"] = {
        **dataset,
        "identity_column": identity_column,
        "latest_id_column": latest_id_column,
    }
    normalized["source_path"] = source
    return normalized


@lru_cache(maxsize=1)
def load_registry() -> dict[str, dict]:
    registry_dir = Path(settings.SURVEY_REGISTRY_DIR).resolve()
    if not registry_dir.is_dir():
        raise SurveyRegistryError(f"Folder Survey Registry tidak ditemukan: {registry_dir}.")

    registry = {}
    for source in sorted(registry_dir.glob("*.json")):
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SurveyRegistryError(f"JSON registry tidak valid: {source}: {exc}") from exc
        if not isinstance(payload, dict):
            raise SurveyRegistryError(f"{source}: root JSON harus berupa object.")
        manifest = _validate_manifest(payload, source)
        if manifest["code"] in registry:
            raise SurveyRegistryError(f"Survey code duplikat: {manifest['code']}.")
        registry[manifest["code"]] = manifest

    if not registry:
        raise SurveyRegistryError(f"Tidak ada manifest survei di {registry_dir}.")
    return registry


def active_survey_code() -> str:
    return str(settings.ACTIVE_SURVEY_CODE).strip().lower()


def get_survey(code: str | None = None) -> dict:
    selected = str(code or active_survey_code()).strip().lower()
    manifest = load_registry().get(selected)
    if not manifest:
        raise SurveyRegistryError(f"Survey code tidak terdaftar: {selected}.")
    if not manifest["enabled"]:
        raise SurveyRegistryError(f"Survei tidak aktif: {selected}.")
    return manifest


def enabled_surveys() -> list[dict]:
    return [manifest for manifest in load_registry().values() if manifest["enabled"]]


def clear_registry_cache() -> None:
    load_registry.cache_clear()
