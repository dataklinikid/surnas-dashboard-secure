from surnasdes26.services.dataset import get_dataset
from surnasdes26.services.metadata import multiple_answer_groups
from surnasdes26.services.tabulation import canonical_code

code = "provntt_nov24"
df = get_dataset(force_refresh=True, survey_code=code)
groups = multiple_answer_groups(code)

print("DATASET_ROWS=", len(df))

for group_name, specification in groups.items():
    columns = [
        option["column"]
        for option in specification["options"]
    ]

    helper = df[columns].apply(
        lambda series: series.map(canonical_code)
    )

    parent = (
        df[group_name].map(canonical_code)
        if group_name in df.columns
        else None
    )

    eligible_current = int(
        helper.ne("").any(axis=1).sum()
    )
    any_selected = int(
        helper.eq("1").any(axis=1).sum()
    )
    selection_total = int(
        helper.eq("1").sum().sum()
    )
    all_zero = int(
        helper.eq("0").all(axis=1).sum()
    )

    print()
    print("GROUP=", group_name)
    print("CURRENT_ELIGIBLE=", eligible_current)
    print("ANY_SELECTED=", any_selected)
    print("SELECTION_TOTAL=", selection_total)
    print("ALL_SIX_ZERO=", all_zero)

    if parent is not None:
        print("PARENT_NONBLANK=", int(parent.ne("").sum()))
        print(
            "PARENT_VALUES=",
            parent.value_counts(dropna=False).head(20).to_dict(),
        )

    for column in columns:
        print(
            "HELPER_VALUES=",
            column,
            helper[column].value_counts(
                dropna=False
            ).to_dict(),
        )
