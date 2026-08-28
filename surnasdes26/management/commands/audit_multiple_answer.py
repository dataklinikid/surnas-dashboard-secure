import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from surnasdes26.services.dataset import DatasetUnavailable, get_dataset
from surnasdes26.services.tabulation import canonical_code


MULTIPLE_ANSWER_GROUPS = {
    "Q_34": {
        "label": "Sumber informasi tentang Danantara",
        "helper": "Q_34C",
        "options": ["Televisi", "Media online", "Media sosial", "Sosialisasi pemerintah/institusi", "Teman/Keluarga", "Lainnya", "Tidak tahu/Tidak jawab"],
    },
    "Q_40_B": {
        "label": "Manfaat program Makan Bergizi Gratis",
        "helper": "Q_40_BC",
        "options": ["Meningkatkan asupan gizi anak", "Mengurangi beban pengeluaran keluarga", "Meningkatkan kehadiran anak di sekolah", "Meningkatkan kesehatan ibu hamil/lansia", "Tidak melihat manfaat signifikan", "Lainnya", "Tidak tahu/Tidak jawab"],
    },
    "Q_40_F": {
        "label": "Masalah pelaksanaan Makan Bergizi Gratis",
        "helper": "Q_40_FC",
        "options": ["Kualitas makanan kurang baik", "Distribusi tidak merata", "Keterlambatan pengiriman", "Kurangnya pengawasan", "Lainnya", "Tidak tahu/Tidak jawab"],
    },
    "Q_40_I": {
        "label": "Hal yang perlu diperbaiki dari program Makan Bergizi Gratis",
        "helper": "Q_40_IC",
        "options": ["Kualitas makanan", "Standar keamanan pangan", "Pengawasan dan kontrol kualitas", "Distribusi dan ketepatan waktu", "Transparansi anggaran", "Sosialisasi program", "Tidak perlu perbaikan", "Lainnya", "Tidak tahu/Tidak jawab"],
    },
    "Q_57": {
        "label": "Jenis bantuan sosial yang pernah diterima",
        "helper": "Q_57C",
        "options": ["Bansos beras", "Program Keluarga Harapan", "Bantuan Pangan Non Tunai", "Program Indonesia Pintar", "Bantuan Subsidi Upah", "Lainnya", "Tidak tahu/Tidak jawab"],
    },
    "Q_63": {
        "label": "Jenis kejahatan yang dialami",
        "helper": "Q_63C",
        "options": ["Pencurian di rumah", "Pencurian kendaraan", "Penipuan online/offline", "Penggelapan", "Perusakan properti", "Lainnya", "Tidak tahu/Tidak jawab"],
    },
    "Q_130": {
        "label": "Hal yang perlu diperbaiki dari institusi kepolisian",
        "helper": "Q_130C",
        "options": ["Kecepatan respons terhadap laporan", "Keramahan dan sikap pelayanan", "Ketegasan dalam penegakan hukum", "Keadilan dan tidak tebang pilih", "Transparansi proses penanganan kasus", "Profesionalitas anggota", "Pemberantasan oknum nakal", "Pendekatan humanis", "Lainnya"],
    },
}


class Command(BaseCommand):
    help = "Mengaudit coding helper multiple-answer tanpa mengekspor baris responden."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="local_artifacts/surnasfeb26_multiple_answer_audit.json",
            help="Lokasi file JSON audit relatif terhadap root project.",
        )

    def handle(self, *args, **options):
        try:
            frame = get_dataset(force_refresh=True)
        except DatasetUnavailable as exc:
            raise CommandError(str(exc)) from exc

        groups = []
        all_observed_codes = set()
        missing_helper_columns = []

        for parent, spec in MULTIPLE_ANSWER_GROUPS.items():
            parent_n = 0
            if parent in frame.columns:
                parent_n = int(frame[parent].map(canonical_code).ne("").sum())

            option_results = []
            for index, option_label in enumerate(spec["options"], start=1):
                column = f'{spec["helper"]}({index})'
                if column not in frame.columns:
                    missing_helper_columns.append(column)
                    continue
                codes = frame[column].map(canonical_code)
                counts = codes.value_counts(dropna=False).to_dict()
                normalized_counts = {
                    (code if code else "(blank)"): int(count)
                    for code, count in sorted(counts.items(), key=lambda item: item[0])
                }
                observed = sorted(code for code in set(codes) if code)
                all_observed_codes.update(observed)
                option_results.append(
                    {
                        "column": column,
                        "option": option_label,
                        "observed_codes": observed,
                        "value_counts": normalized_counts,
                    }
                )

            groups.append(
                {
                    "parent": parent,
                    "label": spec["label"],
                    "parent_answered_n": parent_n,
                    "helper": spec["helper"],
                    "options": option_results,
                }
            )

        payload = {
            "survey_code": "surnasfeb26",
            "contains_respondent_rows": False,
            "row_count": int(len(frame)),
            "group_count": len(groups),
            "all_observed_helper_codes": sorted(all_observed_codes),
            "missing_helper_columns": missing_helper_columns,
            "groups": groups,
        }

        output_path = (settings.BASE_DIR / Path(options["output"])).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"Audit multiple-answer tersimpan di: {output_path}"))
        self.stdout.write(f"Kelompok: {len(groups)}")
        self.stdout.write(
            f"Kode helper teramati: {', '.join(sorted(all_observed_codes)) if all_observed_codes else 'tidak ada'}"
        )
        self.stdout.write(
            f"Kolom helper hilang: {len(missing_helper_columns)}"
        )
        self.stdout.write("Tidak ada baris responden yang diekspor.")
