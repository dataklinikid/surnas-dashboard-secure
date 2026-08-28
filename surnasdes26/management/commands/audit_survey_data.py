import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from surnasdes26.services.dataset import DatasetUnavailable, get_dataset
from surnasdes26.services.metadata import allowed_variables, load_metadata
from surnasdes26.services.tabulation import canonical_code


DIRECT_IDENTIFIER_COLUMNS = {"Q_G", "Q_I", "Q_J", "Q_V", "Q_W", "Q_AC", "HPID", "USRNM"}
MULTIPLE_ANSWER_HELPERS = ["Q_34C", "Q_40_BC", "Q_40_FC", "Q_40_IC", "Q_57C", "Q_63C", "Q_130C"]
WEIGHT_PATTERN = re.compile(r"(^|_)(WEIGHT|BOBOT|PENIMBANG|WGT|RAKE)($|_)", re.IGNORECASE)


class Command(BaseCommand):
    help = "Mengaudit agregat Surnas Februari 2026 tanpa mengekspor baris responden."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="local_artifacts/surnasfeb26_data_audit.json",
            help="Lokasi file JSON audit relatif terhadap root project.",
        )

    def handle(self, *args, **options):
        try:
            frame = get_dataset(force_refresh=True)
        except DatasetUnavailable as exc:
            raise CommandError(str(exc)) from exc

        metadata = load_metadata()
        variables = allowed_variables()
        findings = []
        missing_columns = []
        unknown_code_variables = []
        all_missing_variables = []
        high_missing_variables = []

        for variable, spec in variables.items():
            if variable not in frame.columns:
                missing_columns.append(variable)
                continue

            codes = frame[variable].map(canonical_code)
            nonempty = codes[codes.ne("")]
            observed_codes = sorted(set(nonempty), key=lambda value: (len(value), value))
            known_codes = {str(code) for code in spec.get("values", {})}
            unknown_codes = sorted(set(observed_codes) - known_codes)
            missing_n = int(len(frame) - len(nonempty))
            missing_pct = round((missing_n / len(frame)) * 100, 2) if len(frame) else 0.0

            if unknown_codes:
                unknown_code_variables.append(variable)
            if not observed_codes:
                all_missing_variables.append(variable)
            if missing_pct >= 50:
                high_missing_variables.append(variable)

            findings.append(
                {
                    "variable": variable,
                    "label": spec.get("label", variable),
                    "section": spec.get("section", ""),
                    "n_nonmissing": int(len(nonempty)),
                    "n_missing": missing_n,
                    "missing_pct": missing_pct,
                    "observed_codes": observed_codes,
                    "unknown_codes": unknown_codes,
                }
            )

        identifier_leaks = sorted(DIRECT_IDENTIFIER_COLUMNS.intersection(variables))
        weight_candidates = sorted(column for column in frame.columns if WEIGHT_PATTERN.search(column))
        multiple_answer_columns = {
            helper: sorted(column for column in frame.columns if column.startswith(f"{helper}(") or column == helper)
            for helper in MULTIPLE_ANSWER_HELPERS
        }

        payload = {
            "survey": metadata.get("survey", {}),
            "audit_scope": "aggregate allowlist only",
            "contains_respondent_rows": False,
            "row_count": int(len(frame)),
            "column_count": int(len(frame.columns)),
            "target_n": int(settings.SURNAS_TARGET_N),
            "duplicate_q_ac": int(frame["Q_AC"].duplicated().sum()) if "Q_AC" in frame.columns else None,
            "h0_id_available": "H0_ID" in frame.columns,
            "metadata_variable_count": len(variables),
            "available_metadata_variables": len(variables) - len(missing_columns),
            "missing_metadata_columns": missing_columns,
            "variables_with_unknown_codes": unknown_code_variables,
            "all_missing_variables": all_missing_variables,
            "high_missing_variables": high_missing_variables,
            "direct_identifier_leaks": identifier_leaks,
            "weight_candidates": weight_candidates,
            "multiple_answer_columns": multiple_answer_columns,
            "variable_findings": findings,
        }

        output_path = (settings.BASE_DIR / Path(options["output"])).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Audit tersimpan di: {output_path}"))
        self.stdout.write(f"Baris unik: {len(frame)} dari target {settings.SURNAS_TARGET_N}")
        self.stdout.write(f"Variabel metadata tersedia: {len(variables) - len(missing_columns)}/{len(variables)}")
        self.stdout.write(f"Variabel dengan kode di luar dictionary: {len(unknown_code_variables)}")
        self.stdout.write(f"Variabel seluruhnya kosong: {len(all_missing_variables)}")
        self.stdout.write(f"Variabel missing >=50%: {len(high_missing_variables)}")
        self.stdout.write(f"Kandidat bobot: {', '.join(weight_candidates) if weight_candidates else 'tidak ditemukan'}")
        self.stdout.write(f"Kebocoran identifier ke allowlist: {', '.join(identifier_leaks) if identifier_leaks else 'tidak ada'}")
