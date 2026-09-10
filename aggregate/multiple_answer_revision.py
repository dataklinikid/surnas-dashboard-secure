from copy import deepcopy


def revise_compact_groups(payload, group_names, eligibility):
    revised = deepcopy(payload)
    groups = revised.get("multiple_answer_groups")
    if not isinstance(groups, dict):
        raise ValueError("Metadata tidak memiliki multiple_answer_groups yang valid.")

    for name in group_names:
        specification = groups.get(name)
        if not isinstance(specification, dict):
            raise ValueError(f"Kelompok multiple-answer {name} tidak ditemukan.")
        options = specification.get("options", [])
        codes = [str(option.get("source_code", "")) for option in options]
        if not codes or any(len(code) != 1 for code in codes):
            raise ValueError(f"Kelompok {name} tidak memakai kode opsi satu karakter.")
        if len(set(codes)) != len(codes):
            raise ValueError(f"Kelompok {name} memiliki source_code duplikat.")
        specification.update(
            storage="compact_codes",
            source_column=name,
            eligibility=eligibility,
        )
    return revised
