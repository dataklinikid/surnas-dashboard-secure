from collections.abc import Mapping

import pandas as pd


VALID_CROSSTAB_OUTPUTS = {"count", "row_percentage", "column_percentage", "total_percentage"}
MAX_CROSSTAB_CATEGORIES = 100


class InvalidTabulation(ValueError):
    pass


def canonical_code(value) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _category_order(series: pd.Series, labels: Mapping[str, str]) -> list[str]:
    observed = [canonical_code(value) for value in series.dropna().unique()]
    return list(dict.fromkeys([*map(str, labels.keys()), *observed]))


def frequency_table(
    df: pd.DataFrame,
    variable: str,
    labels: Mapping[str, str],
    weight_variable: str | None = None,
) -> dict:
    if variable not in df.columns:
        raise InvalidTabulation(f"Variabel {variable} tidak tersedia pada dataset.")

    frame = pd.DataFrame({"code": df[variable].map(canonical_code)})
    frame = frame[frame["code"].ne("")]
    order = _category_order(df[variable], labels)
    unweighted_counts = frame["code"].value_counts(sort=False).reindex(order, fill_value=0)

    if weight_variable:
        if weight_variable not in df.columns:
            raise InvalidTabulation(f"Variabel bobot {weight_variable} tidak tersedia.")
        frame["weight"] = pd.to_numeric(df.loc[frame.index, weight_variable], errors="coerce").fillna(0)
        counts = frame.groupby("code", sort=False)["weight"].sum().reindex(order, fill_value=0.0)
    else:
        counts = unweighted_counts

    total = float(counts.sum())
    percentages = counts.div(total).mul(100) if total else counts.astype(float)
    unweighted_total = int(unweighted_counts.sum())
    unweighted_percentages = (
        unweighted_counts.div(unweighted_total).mul(100)
        if unweighted_total
        else unweighted_counts.astype(float)
    )
    rows = [
        {
            "code": code,
            "label": labels.get(code, code),
            "count": round(float(counts.loc[code]), 3),
            "unweighted_count": int(unweighted_counts.loc[code]),
            "unweighted_percentage": round(float(unweighted_percentages.loc[code]), 1),
            "percentage": round(float(percentages.loc[code]), 1),
        }
        for code in order
    ]
    return {
        "rows": rows,
        "n_total": int(len(df)),
        "n_valid": int(len(frame)),
        "weighted": bool(weight_variable),
        "weighted_base": round(total, 3),
    }


def crosstab_table(
    df: pd.DataFrame,
    row_variable: str,
    column_variable: str,
    row_labels: Mapping[str, str],
    column_labels: Mapping[str, str],
    output_type: str = "row_percentage",
    weight_variable: str | None = None,
) -> dict:
    if output_type not in VALID_CROSSTAB_OUTPUTS:
        raise InvalidTabulation("Jenis keluaran crosstab tidak valid.")
    missing = [name for name in (row_variable, column_variable) if name not in df.columns]
    if missing:
        raise InvalidTabulation(f"Variabel tidak tersedia: {', '.join(missing)}")
    if row_variable == column_variable:
        raise InvalidTabulation("Variabel baris dan kolom harus berbeda.")
    if weight_variable and weight_variable not in df.columns:
        raise InvalidTabulation(f"Variabel bobot {weight_variable} tidak tersedia.")

    frame = pd.DataFrame(
        {
            "row": df[row_variable].map(canonical_code),
            "column": df[column_variable].map(canonical_code),
        }
    )
    if weight_variable:
        frame["weight"] = pd.to_numeric(df[weight_variable], errors="coerce")
    frame = frame[(frame["row"] != "") & (frame["column"] != "")]
    if weight_variable and (frame["weight"].isna().any() or frame["weight"].le(0).any()):
        raise InvalidTabulation("Bobot crosstab harus numerik dan lebih besar dari nol.")
    row_order = _category_order(df[row_variable], row_labels)
    column_order = _category_order(df[column_variable], column_labels)
    if len(row_order) > MAX_CROSSTAB_CATEGORIES or len(column_order) > MAX_CROSSTAB_CATEGORIES:
        raise InvalidTabulation(
            "Crosstab dibatasi maksimal "
            f"{MAX_CROSSTAB_CATEGORIES} kategori pada setiap dimensi."
        )
    raw_counts = pd.crosstab(frame["row"], frame["column"], dropna=False).reindex(
        index=row_order, columns=column_order, fill_value=0
    )
    if weight_variable:
        counts = frame.pivot_table(
            index="row",
            columns="column",
            values="weight",
            aggfunc="sum",
            fill_value=0,
        ).reindex(index=row_order, columns=column_order, fill_value=0.0)
    else:
        counts = raw_counts.astype(float)

    row_denominator = counts.sum(axis=1).replace(0, pd.NA)
    column_denominator = counts.sum(axis=0).replace(0, pd.NA)
    grand_total = int(raw_counts.to_numpy().sum())
    weighted_grand_total = float(counts.to_numpy().sum())
    matrices = {
        "count": counts.astype(float),
        "row_percentage": counts.div(row_denominator, axis=0).mul(100).fillna(0),
        "column_percentage": counts.div(column_denominator, axis=1).mul(100).fillna(0),
        "total_percentage": (
            counts.div(weighted_grand_total).mul(100)
            if weighted_grand_total
            else counts.astype(float)
        ),
    }
    result = matrices[output_type]

    rows = []
    for row_code in row_order:
        cells = []
        for col_code in column_order:
            cells.append(
                {
                    "count": int(raw_counts.loc[row_code, col_code]),
                    "weighted_count": round(float(counts.loc[row_code, col_code]), 3),
                    "row_percentage": round(
                        float(matrices["row_percentage"].loc[row_code, col_code]), 1
                    ),
                    "column_percentage": round(
                        float(matrices["column_percentage"].loc[row_code, col_code]), 1
                    ),
                    "total_percentage": round(
                        float(matrices["total_percentage"].loc[row_code, col_code]), 1
                    ),
                    "display": (
                        round(float(counts.loc[row_code, col_code]), 3)
                        if output_type == "count"
                        else round(float(result.loc[row_code, col_code]), 1)
                    ),
                }
            )
        rows.append(
            {
                "code": row_code,
                "label": row_labels.get(row_code, row_code),
                "values": [round(float(result.loc[row_code, col_code]), 1) for col_code in column_order],
                "cells": cells,
                "n": int(raw_counts.loc[row_code].sum()),
                "weighted_n": round(float(counts.loc[row_code].sum()), 3),
                "display_total": (
                    round(float(counts.loc[row_code].sum()), 3)
                    if output_type == "count"
                    else (
                        100.0
                        if output_type == "row_percentage" and float(counts.loc[row_code].sum())
                        else (
                            round(float(counts.loc[row_code].sum()) / weighted_grand_total * 100, 1)
                            if output_type == "total_percentage" and weighted_grand_total
                            else None
                        )
                    )
                ),
            }
        )
    column_totals = [int(raw_counts[column_code].sum()) for column_code in column_order]
    weighted_column_totals = [
        round(float(counts[column_code].sum()), 3) for column_code in column_order
    ]
    base_output_label = {
        "count": "Frekuensi",
        "row_percentage": "Persentase per baris",
        "column_percentage": "Persentase per kolom",
        "total_percentage": "Persentase dari total valid",
    }[output_type]
    output_label = f"{base_output_label} berbobot" if weight_variable else base_output_label
    if output_type == "count":
        display_column_totals = weighted_column_totals
        display_grand_total = round(weighted_grand_total, 3)
    elif output_type == "column_percentage":
        display_column_totals = [
            100.0 if float(counts[column_code].sum()) else 0.0
            for column_code in column_order
        ]
        display_grand_total = None
    elif output_type == "total_percentage":
        display_column_totals = [
            round(float(counts[column_code].sum()) / weighted_grand_total * 100, 1)
            if weighted_grand_total
            else 0.0
            for column_code in column_order
        ]
        display_grand_total = 100.0 if weighted_grand_total else 0.0
    else:
        display_column_totals = []
        display_grand_total = None
    return {
        "columns": [{"code": code, "label": column_labels.get(code, code)} for code in column_order],
        "rows": rows,
        "column_totals": column_totals,
        "weighted_column_totals": weighted_column_totals,
        "grand_total": grand_total,
        "weighted_grand_total": round(weighted_grand_total, 3),
        "n_total": int(len(df)),
        "n_valid": int(len(frame)),
        "n_missing": int(len(df) - len(frame)),
        "n_missing_row": int(df[row_variable].map(canonical_code).eq("").sum()),
        "n_missing_column": int(df[column_variable].map(canonical_code).eq("").sum()),
        "output_type": output_type,
        "output_label": output_label,
        "is_percentage": output_type != "count",
        "weighted": bool(weight_variable),
        "row_total_label": "Weighted total baris" if weight_variable else "N",
        "column_total_label": "Weighted total kolom" if weight_variable else "Total n valid kolom",
        "show_row_total": output_type != "column_percentage",
        "show_column_total": output_type != "row_percentage",
        "display_column_totals": display_column_totals,
        "display_grand_total": display_grand_total,
        "display_total_label": (
            ("Weighted total" if weight_variable else "Total")
            if output_type == "count"
            else "Total %"
        ),
    }


def multiple_answer_table(
    df: pd.DataFrame,
    group_name: str,
    specification: Mapping,
    weight_variable: str | None = None,
) -> dict:
    options = specification.get("options", [])
    if not isinstance(options, list) or not options:
        raise InvalidTabulation(f"Opsi multiple-answer {group_name} tidak tersedia.")
    columns = [str(option.get("column", "")) for option in options]
    missing = [column for column in columns if not column or column not in df.columns]
    if missing:
        raise InvalidTabulation(
            f"Kolom helper multiple-answer tidak tersedia: {', '.join(missing)}"
        )
    if specification.get("eligibility") != "any_helper_not_blank":
        raise InvalidTabulation("Aturan denominator multiple-answer tidak didukung.")
    if weight_variable and weight_variable not in df.columns:
        raise InvalidTabulation(f"Variabel bobot {weight_variable} tidak tersedia.")

    selected_value = str(specification.get("selected_value", "1"))
    helper = pd.DataFrame(
        {column: df[column].map(canonical_code) for column in columns},
        index=df.index,
    )
    eligible_mask = helper.ne("").any(axis=1)
    eligible = helper.loc[eligible_mask]
    eligible_n = int(len(eligible))
    if weight_variable:
        weights = pd.to_numeric(df.loc[eligible.index, weight_variable], errors="coerce")
        if weights.isna().any() or weights.le(0).any():
            raise InvalidTabulation("Bobot multiple-answer harus numerik dan lebih besar dari nol.")
    else:
        weights = pd.Series(1.0, index=eligible.index)
    weighted_eligible = float(weights.sum())

    rows = []
    selection_total = 0
    weighted_selection_total = 0.0
    for option, column in zip(options, columns):
        selected_mask = eligible[column].eq(selected_value)
        count = int(selected_mask.sum())
        weighted_count = float(weights[selected_mask].sum())
        selection_total += count
        weighted_selection_total += weighted_count
        percentage = (
            weighted_count / weighted_eligible * 100 if weighted_eligible else 0.0
        )
        rows.append(
            {
                "index": int(option.get("index", len(rows) + 1)),
                "code": str(option.get("source_code", option.get("index", ""))),
                "column": column,
                "label": str(option.get("label", column)),
                "count": count,
                "weighted_count": round(weighted_count, 3),
                "percentage": round(percentage, 1),
            }
        )

    return {
        "group": group_name,
        "label": str(specification.get("label", group_name)),
        "rows": rows,
        "n_total": int(len(df)),
        "n_eligible": eligible_n,
        "weighted_eligible": round(weighted_eligible, 3),
        "selection_total": selection_total,
        "weighted_selection_total": round(weighted_selection_total, 3),
        "mean_selections": (
            round(weighted_selection_total / weighted_eligible, 2)
            if weighted_eligible
            else 0.0
        ),
        "denominator_rule": "any_helper_not_blank",
        "percentages_sum_to_100": False,
        "weighted": bool(weight_variable),
    }
