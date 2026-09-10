def monitoring_target_progress(completed, raw_target):
    """Return optional target/progress without failing on an unset target."""
    if raw_target is None or raw_target == "":
        return None, None
    try:
        target = int(raw_target)
    except (TypeError, ValueError):
        return None, None
    if target <= 0:
        return None, None
    return target, round((completed / target) * 100, 1)


def _status(actual, target):
    if actual <= 0:
        return "Belum mulai"
    if actual < target:
        return "Berjalan"
    if actual == target:
        return "Target tercapai"
    return "Melebihi target"


def psu_monitoring_summary(df, monitoring):
    """Build a read-only operational summary from unique questionnaire numbers."""
    frame = (monitoring or {}).get("psu_frame")
    columns = (monitoring or {}).get("columns", {})
    questionnaire_column = columns.get("questionnaire", "")
    if not frame or not questionnaire_column or questionnaire_column not in df.columns:
        return None

    import pandas as pd

    questionnaire = pd.to_numeric(df[questionnaire_column], errors="coerce")
    questionnaire = questionnaire.where(questionnaire.mod(1).eq(0))
    valid_numbers = questionnaire.dropna().astype("int64")
    duplicate_count = int(valid_numbers.duplicated(keep=False).sum())
    unique_numbers = set(valid_numbers.unique().tolist())
    matched_numbers = set()
    psu_rows = []
    for row in frame.get("rows", []):
        start = int(row["questionnaire_start"])
        end = int(row["questionnaire_end"])
        numbers = {number for number in unique_numbers if start <= number <= end}
        matched_numbers.update(numbers)
        actual = len(numbers)
        target = int(row["target_n"])
        psu_rows.append(
            {
                **row,
                "actual": actual,
                "remaining": max(target - actual, 0),
                "excess": max(actual - target, 0),
                "progress": round((actual / target) * 100, 1) if target else None,
                "status": _status(actual, target),
            }
        )

    def aggregate(field):
        result = {}
        for row in psu_rows:
            label = row.get(field) or "Tidak diketahui"
            item = result.setdefault(label, {"label": label, "psu_count": 0, "target": 0, "actual": 0})
            item["psu_count"] += 1
            item["target"] += row["target_n"]
            item["actual"] += row["actual"]
        for item in result.values():
            item["remaining"] = max(item["target"] - item["actual"], 0)
            item["progress"] = round((item["actual"] / item["target"]) * 100, 1) if item["target"] else None
        return sorted(result.values(), key=lambda item: item["label"])

    enumerator_rows = []
    enumerator_column = columns.get("enumerator", "")
    if enumerator_column and enumerator_column in df.columns:
        working = pd.DataFrame(
            {"number": questionnaire, "enumerator": df[enumerator_column].fillna("").astype(str).str.strip()}
        ).dropna(subset=["number"])
        working["number"] = working["number"].astype("int64")
        working = working[working["number"].isin(matched_numbers)].drop_duplicates("number")
        counts = working["enumerator"].replace("", "Tidak diisi").value_counts()
        enumerator_rows = [
            {"label": label, "actual": int(count)} for label, count in counts.items()
        ]

    target_total = int(frame["target_total"])
    actual_total = len(matched_numbers)
    return {
        "frame_version": frame["version"],
        "target": target_total,
        "actual": actual_total,
        "remaining": max(target_total - actual_total, 0),
        "excess": max(actual_total - target_total, 0),
        "progress": round((actual_total / target_total) * 100, 1) if target_total else None,
        "unmatched": len(unique_numbers - matched_numbers),
        "missing_questionnaire": int(questionnaire.isna().sum()),
        "duplicate_rows": duplicate_count,
        "psu_rows": psu_rows,
        "regency_rows": aggregate("regency"),
        "dpr_ri_rows": aggregate("dpr_ri_constituency"),
        "urban_rural_rows": aggregate("urban_rural"),
        "enumerator_rows": enumerator_rows,
    }
