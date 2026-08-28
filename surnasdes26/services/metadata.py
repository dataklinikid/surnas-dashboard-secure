import json
from functools import lru_cache

from surnasdes26.services.registry import get_survey


@lru_cache(maxsize=16)
def load_metadata(survey_code: str | None = None) -> dict:
    survey = get_survey(survey_code)
    metadata_path = survey["metadata"]["resolved_path"]
    with metadata_path.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    variables = payload.get("variables", {})
    if not isinstance(variables, dict):
        raise ValueError("metadata.json harus memiliki object 'variables'.")
    metadata_code = str(payload.get("survey", {}).get("code", "")).strip().lower()
    if metadata_code and metadata_code != survey["code"]:
        raise ValueError(
            f"Survey code metadata '{metadata_code}' tidak cocok dengan registry '{survey['code']}'."
        )
    return payload


def allowed_variables(survey_code: str | None = None) -> dict[str, dict]:
    return load_metadata(survey_code)["variables"]


def variable_choices(columns=None, survey_code: str | None = None) -> list[tuple[str, str]]:
    variables = allowed_variables(survey_code)
    allowed_columns = set(variables if columns is None else columns)
    return [
        (name, spec.get("label", name))
        for name, spec in variables.items()
        if name in allowed_columns and spec.get("values")
    ]


def grouped_variable_choices(columns=None, survey_code: str | None = None) -> list[dict]:
    variables = allowed_variables(survey_code)
    allowed_columns = set(variables if columns is None else columns)
    groups = {}
    for name, spec in variables.items():
        if name not in allowed_columns or not spec.get("values"):
            continue
        section = str(spec.get("section", "Variabel lainnya"))
        groups.setdefault(section, []).append((name, spec.get("label", name)))
    return [{"label": section, "choices": choices} for section, choices in groups.items()]


def value_labels(variable: str, survey_code: str | None = None) -> dict[str, str]:
    spec = allowed_variables(survey_code).get(variable)
    if not spec:
        raise ValueError(f"Variabel {variable} tidak terdaftar.")
    return {str(key): str(value) for key, value in spec.get("values", {}).items()}


def variable_label(variable: str, survey_code: str | None = None) -> str:
    spec = allowed_variables(survey_code).get(variable)
    if not spec:
        raise ValueError(f"Variabel {variable} tidak terdaftar.")
    return str(spec.get("label", variable))


def multiple_answer_groups(survey_code: str | None = None) -> dict[str, dict]:
    groups = load_metadata(survey_code).get("multiple_answer_groups", {})
    if not isinstance(groups, dict):
        raise ValueError("multiple_answer_groups harus berupa object.")
    return groups


def multiple_answer_choices(survey_code: str | None = None) -> list[tuple[str, str]]:
    return [
        (name, str(spec.get("label", name)))
        for name, spec in multiple_answer_groups(survey_code).items()
    ]
