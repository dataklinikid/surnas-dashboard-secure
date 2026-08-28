import json
import re
import tempfile
from datetime import datetime
from pathlib import Path

from django.conf import settings

from surnasdes26.services.metadata import load_metadata
from surnasdes26.services.registry import SurveyRegistryError, clear_registry_cache
from surnasdes26.services.sectioning import classify_metadata_sections


CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
ALIAS_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
ENV_PREFIX_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")


class SurveyRegistrationError(ValueError):
    pass


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SurveyRegistrationError(f"JSON tidak valid: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SurveyRegistrationError(f"Root JSON harus berupa object: {path}.")
    return payload


def validate_canonical_metadata(path: str | Path) -> dict:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise SurveyRegistrationError(f"Canonical metadata tidak ditemukan: {source}.")
    payload = _read_json(source)
    if payload.get("metadata_schema_version") != 1:
        raise SurveyRegistrationError("metadata_schema_version yang didukung hanya 1.")

    survey = payload.get("survey")
    variables = payload.get("variables")
    groups = payload.get("multiple_answer_groups", {})
    report = payload.get("build_report", {})
    if not isinstance(survey, dict):
        raise SurveyRegistrationError("Object survey tidak ditemukan pada canonical metadata.")
    if not isinstance(variables, dict) or not variables:
        raise SurveyRegistrationError("Object variables kosong atau tidak valid.")
    if not isinstance(groups, dict):
        raise SurveyRegistrationError("multiple_answer_groups harus berupa object.")

    code = str(survey.get("code", "")).strip().lower()
    name = str(survey.get("name", "")).strip()
    if not CODE_PATTERN.fullmatch(code):
        raise SurveyRegistrationError(f"Survey code tidak valid: {code!r}.")
    if not name:
        raise SurveyRegistrationError("Nama survei wajib tersedia pada canonical metadata.")
    if not bool(survey.get("aggregate_only")):
        raise SurveyRegistrationError("Canonical metadata wajib aggregate_only=true.")
    if report.get("contains_respondent_rows") is not False:
        raise SurveyRegistrationError("Canonical metadata belum menyatakan contains_respondent_rows=false.")

    return payload


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(path)


def _preserve_sections(canonical: dict, existing_metadata_path: Path | None) -> int:
    if not existing_metadata_path or not existing_metadata_path.is_file():
        return 0
    existing = _read_json(existing_metadata_path)
    existing_variables = existing.get("variables", {})
    if not isinstance(existing_variables, dict):
        return 0

    preserved = 0
    for variable, spec in canonical["variables"].items():
        old_spec = existing_variables.get(variable)
        if not isinstance(old_spec, dict) or not old_spec.get("section"):
            continue
        spec["section"] = old_spec["section"]
        preserved += 1
    return preserved


def build_registration_plan(
    canonical_path: str | Path,
    *,
    database_alias: str | None = None,
    env_prefix: str | None = None,
    identity_column: str | None = None,
    latest_id_column: str | None = None,
    target_n: int | None = None,
    enable: bool = False,
    section_reference_code: str | None = None,
) -> dict:
    canonical = validate_canonical_metadata(canonical_path)
    code = canonical["survey"]["code"]
    registry_dir = Path(settings.SURVEY_REGISTRY_DIR).resolve()
    manifest_path = registry_dir / f"{code}.json"
    existing_manifest = _read_json(manifest_path) if manifest_path.is_file() else None

    if existing_manifest:
        database = dict(existing_manifest.get("database", {}))
        dataset = dict(existing_manifest.get("dataset", {}))
        privacy = dict(existing_manifest.get("privacy", {}))
        dashboard = dict(existing_manifest.get("dashboard", {}))
        enabled = bool(existing_manifest.get("enabled", True))
        old_metadata_value = str(existing_manifest.get("metadata", {}).get("path", "")).strip()
        existing_metadata_path = (
            (settings.BASE_DIR / old_metadata_value).resolve() if old_metadata_value else None
        )
    else:
        alias = database_alias or f"survey_{code}_db"
        prefix = env_prefix or f"SURVEY_{code.upper()}_DB"
        database = {
            "alias": alias,
            "env_prefix": prefix,
            "table": str(canonical["survey"].get("source_table", "h0")),
            "legacy_source": True,
        }
        dataset = {
            "identity_column": identity_column or "Q_AC",
            "latest_id_column": latest_id_column or "H0_ID",
            "target_n": int(target_n or 0),
        }
        privacy = {"aggregate_only": True}
        dashboard = {}
        enabled = bool(enable)
        existing_metadata_path = None

    if database_alias:
        database["alias"] = database_alias
    if env_prefix:
        database["env_prefix"] = env_prefix
    if identity_column:
        dataset["identity_column"] = identity_column.upper()
    if latest_id_column:
        dataset["latest_id_column"] = latest_id_column.upper()
    if target_n is not None:
        dataset["target_n"] = int(target_n)

    alias = str(database.get("alias", "")).strip()
    prefix = str(database.get("env_prefix", "")).strip().upper()
    if not ALIAS_PATTERN.fullmatch(alias):
        raise SurveyRegistrationError(f"Database alias tidak valid: {alias!r}.")
    if not ENV_PREFIX_PATTERN.fullmatch(prefix):
        raise SurveyRegistrationError(f"Environment prefix tidak valid: {prefix!r}.")
    database["alias"] = alias
    database["env_prefix"] = prefix
    database["table"] = str(database.get("table", "h0")).strip() or "h0"
    database["legacy_source"] = bool(database.get("legacy_source", True))

    identity = str(dataset.get("identity_column", "")).strip().upper()
    if not identity:
        raise SurveyRegistrationError("identity_column wajib diisi.")
    dataset["identity_column"] = identity
    dataset["latest_id_column"] = str(dataset.get("latest_id_column", "")).strip().upper()
    dataset["target_n"] = int(dataset.get("target_n", 0) or 0)

    metadata_relative = Path("survey_metadata") / code / "metadata.json"
    metadata_path = (settings.BASE_DIR / metadata_relative).resolve()
    manifest = {
        "schema_version": 1,
        "code": code,
        "name": canonical["survey"]["name"],
        "enabled": enabled,
        "database": database,
        "metadata": {"path": metadata_relative.as_posix()},
        "dataset": dataset,
        "privacy": {**privacy, "aggregate_only": True},
        "dashboard": dashboard,
    }
    preserved_sections = _preserve_sections(canonical, existing_metadata_path)
    reference_code = str(section_reference_code or "").strip().lower()
    if reference_code == code:
        raise SurveyRegistrationError("Survey target dan referensi section harus berbeda.")
    try:
        reference_metadata = load_metadata(reference_code) if reference_code else None
    except (SurveyRegistryError, ValueError, OSError) as exc:
        raise SurveyRegistrationError(f"Referensi section tidak dapat dibaca: {exc}") from exc
    section_plan = classify_metadata_sections(
        canonical,
        reference_metadata,
        preserve_current=bool(existing_manifest and not reference_code),
    )
    canonical = section_plan["metadata"]

    return {
        "code": code,
        "canonical": canonical,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "metadata_path": metadata_path,
        "existing": existing_manifest is not None,
        "preserved_sections": preserved_sections,
        "section_plan": section_plan,
    }


def apply_registration(plan: dict, *, replace: bool = False) -> dict:
    if plan["existing"] and not replace:
        raise SurveyRegistrationError(
            f"Survei {plan['code']} sudah terdaftar; gunakan --replace untuk memperbarui."
        )

    backup_path = None
    if plan["existing"]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = (
            settings.BASE_DIR
            / "local_artifacts"
            / "registry_backups"
            / f"{plan['code']}_{timestamp}.json"
        )
        _atomic_write_json(backup_path, _read_json(plan["manifest_path"]))

    _atomic_write_json(plan["metadata_path"], plan["canonical"])
    _atomic_write_json(plan["manifest_path"], plan["manifest"])
    clear_registry_cache()
    load_metadata.cache_clear()
    return {**plan, "backup_path": backup_path}
