import json
import re
import zipfile
from pathlib import Path


SECTION_PATTERN = re.compile(r"\[([A-Za-z]+)\]")
OPTION_SUFFIX_PATTERN = re.compile(r"\s*\(\d+\)\s*$")


class MetadataParseError(ValueError):
    pass


def _decode_dictionary(raw: bytes) -> str:
    text = raw.decode("utf-8-sig", errors="strict").replace("\r", "")
    return text.removeprefix("ï»¿")


def _read_bundle(source: Path) -> tuple[str, dict]:
    if source.is_dir():
        dictionary_path = source / "cspro_dictionary.txt"
        schema_path = source / "h0_schema.json"
        if not dictionary_path.is_file() or not schema_path.is_file():
            raise MetadataParseError(
                "Folder sumber wajib memiliki cspro_dictionary.txt dan h0_schema.json."
            )
        dictionary_text = _decode_dictionary(dictionary_path.read_bytes())
        schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))
        return dictionary_text, schema

    if source.suffix.lower() != ".zip" or not source.is_file():
        raise MetadataParseError("Sumber metadata harus berupa folder atau file ZIP.")

    with zipfile.ZipFile(source) as archive:
        names = {Path(name).name.lower(): name for name in archive.namelist() if not name.endswith("/")}
        dictionary_member = names.get("cspro_dictionary.txt")
        schema_member = names.get("h0_schema.json")
        if not dictionary_member or not schema_member:
            raise MetadataParseError(
                "ZIP wajib memiliki cspro_dictionary.txt dan h0_schema.json."
            )
        dictionary_text = _decode_dictionary(archive.read(dictionary_member))
        schema = json.loads(archive.read(schema_member).decode("utf-8-sig"))
        return dictionary_text, schema


def parse_dictionary(text: str) -> tuple[dict, list[dict]]:
    dictionary = {}
    items = []
    section = None
    record_label = "Variabel lainnya"
    current_item = None
    current_value_set = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        section_match = SECTION_PATTERN.fullmatch(line)
        if section_match:
            section = section_match.group(1)
            if section == "Item":
                current_item = {"value_sets": [], "record_label": record_label}
                items.append(current_item)
                current_value_set = None
            elif section == "ValueSet":
                if current_item is None:
                    raise MetadataParseError("ValueSet ditemukan sebelum Item.")
                current_value_set = {"values": []}
                current_item["value_sets"].append(current_value_set)
            else:
                current_value_set = None
            continue

        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if section == "Dictionary":
            dictionary[key] = value
        elif section == "Record" and key == "Label":
            record_label = value or "Variabel lainnya"
        elif section == "Item" and current_item is not None:
            current_item[key] = value
        elif section == "ValueSet" and current_value_set is not None:
            if key == "Value":
                current_value_set["values"].append(value)
            else:
                current_value_set[key] = value

    if not items:
        raise MetadataParseError("Dictionary tidak memiliki section Item.")
    return dictionary, items


def _clean_code(raw: str) -> str:
    return raw.strip().strip("'").strip('"').strip()


def _value_pairs(item: dict) -> list[tuple[str, str]]:
    pairs = []
    seen = set()
    for value_set in item.get("value_sets", []):
        for raw_value in value_set.get("values", []):
            if ";" not in raw_value:
                continue
            raw_code, raw_label = raw_value.split(";", 1)
            code = _clean_code(raw_code)
            label = raw_label.strip().strip('"').strip()
            if not code or not label or ":" in code or code in seen:
                continue
            seen.add(code)
            pairs.append((code, label))
    return pairs


def _occurrences(item: dict) -> int:
    try:
        value = int(item.get("Occurrences", "1"))
    except (TypeError, ValueError) as exc:
        raise MetadataParseError(
            f"Occurrences tidak valid pada {item.get('Name', '(tanpa nama)')}."
        ) from exc
    return max(value, 1)


def build_canonical_metadata(source: str | Path, survey_code: str, survey_name: str) -> dict:
    source_path = Path(source).expanduser().resolve()
    code = survey_code.strip().lower()
    name = survey_name.strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", code):
        raise MetadataParseError("Survey code hanya boleh huruf kecil, angka, dan underscore.")
    if not name:
        raise MetadataParseError("Nama survei wajib diisi.")

    dictionary_text, schema = _read_bundle(source_path)
    dictionary, items = parse_dictionary(dictionary_text)
    schema_items = schema.get("columns")
    if not isinstance(schema_items, list):
        raise MetadataParseError("h0_schema.json harus memiliki array 'columns'.")
    schema_columns = {
        str(column.get("COLUMN_NAME", "")).strip().upper()
        for column in schema_items
        if isinstance(column, dict) and column.get("COLUMN_NAME")
    }
    if not schema_columns:
        raise MetadataParseError("Schema tidak memiliki nama kolom.")

    variables = {}
    multiple_answer_groups = {}
    excluded = {
        "non_numeric": [],
        "without_discrete_labels": [],
        "missing_schema": [],
        "occurrence_helper": [],
    }

    for index, item in enumerate(items):
        variable = str(item.get("Name", "")).strip().upper()
        if not variable:
            continue
        occurrences = _occurrences(item)
        pairs = _value_pairs(item)

        if occurrences > 1:
            excluded["occurrence_helper"].append(variable)
            expected_columns = [f"{variable}({position})" for position in range(1, occurrences + 1)]
            available_columns = [column for column in expected_columns if column in schema_columns]
            missing_columns = [column for column in expected_columns if column not in schema_columns]
            parent = items[index - 1] if index else {}
            parent_name = str(parent.get("Name", "")).strip().upper()
            parent_pairs = _value_pairs(parent)
            is_multiple = "MULTIPLE ANSWER" in str(item.get("Label", "")).upper()
            if is_multiple and parent_name and parent_pairs and available_columns:
                options = []
                for position, (option_code, option_label) in enumerate(parent_pairs, start=1):
                    if position > occurrences:
                        break
                    options.append(
                        {
                            "index": position,
                            "source_code": option_code,
                            "column": f"{variable}({position})",
                            "label": OPTION_SUFFIX_PATTERN.sub("", option_label).strip(),
                        }
                    )
                multiple_answer_groups[parent_name] = {
                    "label": str(parent.get("Label", parent_name)).strip(),
                    "helper_prefix": variable,
                    "selected_value": "1",
                    "unselected_value": "0",
                    "eligibility": "any_helper_not_blank",
                    "options": options,
                    "missing_columns": missing_columns,
                }
            continue

        if variable not in schema_columns:
            excluded["missing_schema"].append(variable)
            continue
        if str(item.get("DataType", "")).strip().lower() != "numeric":
            excluded["non_numeric"].append(variable)
            continue
        if not pairs:
            excluded["without_discrete_labels"].append(variable)
            continue

        variables[variable] = {
            "label": str(item.get("Label", variable)).strip(),
            "section": str(item.get("record_label", "Variabel lainnya")).strip(),
            "values": {code_value: label for code_value, label in pairs},
        }

    table = str(schema.get("table", "h0")).strip() or "h0"
    return {
        "metadata_schema_version": 1,
        "survey": {
            "code": code,
            "name": name,
            "dictionary_name": dictionary.get("Name", ""),
            "dictionary_label": dictionary.get("Label", ""),
            "dictionary_version": dictionary.get("Version", ""),
            "source_table": table,
            "aggregate_only": True,
        },
        "variables": variables,
        "multiple_answer_groups": multiple_answer_groups,
        "build_report": {
            "dictionary_item_count": len(items),
            "schema_column_count": len(schema_columns),
            "categorical_variable_count": len(variables),
            "multiple_answer_group_count": len(multiple_answer_groups),
            "excluded_counts": {key: len(value) for key, value in excluded.items()},
            "excluded": excluded,
            "contains_respondent_rows": False,
        },
    }
