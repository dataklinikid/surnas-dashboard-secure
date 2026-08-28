from django.core.management.base import BaseCommand, CommandError

from surnasdes26.services.registration import (
    SurveyRegistrationError,
    apply_registration,
    build_registration_plan,
)


class Command(BaseCommand):
    help = "Mendaftarkan canonical metadata ke Survey Registry secara aman. Default hanya preview."

    def add_arguments(self, parser):
        parser.add_argument("--metadata", required=True, help="Canonical metadata JSON.")
        parser.add_argument("--database-alias")
        parser.add_argument("--env-prefix")
        parser.add_argument("--identity-column")
        parser.add_argument("--latest-id-column")
        parser.add_argument("--target-n", type=int)
        parser.add_argument(
            "--section-reference",
            help="Survey code referensi untuk menyalin section variabel yang namanya sama.",
        )
        parser.add_argument("--enable", action="store_true", help="Aktifkan survei baru.")
        parser.add_argument("--apply", action="store_true", help="Tulis metadata dan manifest.")
        parser.add_argument("--replace", action="store_true", help="Perbarui survei yang sudah ada.")

    def handle(self, *args, **options):
        try:
            plan = build_registration_plan(
                options["metadata"],
                database_alias=options.get("database_alias"),
                env_prefix=options.get("env_prefix"),
                identity_column=options.get("identity_column"),
                latest_id_column=options.get("latest_id_column"),
                target_n=options.get("target_n"),
                enable=options.get("enable", False),
                section_reference_code=options.get("section_reference"),
            )
            result = (
                apply_registration(plan, replace=options.get("replace", False))
                if options.get("apply")
                else plan
            )
        except (SurveyRegistrationError, OSError) as exc:
            raise CommandError(str(exc)) from exc

        action = "APPLIED" if options.get("apply") else "PREVIEW"
        self.stdout.write(self.style.SUCCESS(f"Register survey: {action}"))
        self.stdout.write(f"Survey code: {result['code']}")
        self.stdout.write(f"Existing survey: {result['existing']}")
        self.stdout.write(f"Enabled: {result['manifest']['enabled']}")
        self.stdout.write(f"Database alias: {result['manifest']['database']['alias']}")
        self.stdout.write(f"Environment prefix: {result['manifest']['database']['env_prefix']}")
        self.stdout.write(f"Variabel: {len(result['canonical']['variables'])}")
        self.stdout.write(
            f"Multiple-answer: {len(result['canonical'].get('multiple_answer_groups', {}))}"
        )
        self.stdout.write(f"Section dipertahankan: {result['preserved_sections']}")
        self.stdout.write(f"Sumber section: {result['section_plan']['source_counts']}")
        self.stdout.write(f"Distribusi section: {result['section_plan']['section_counts']}")
        self.stdout.write(f"Metadata target: {result['metadata_path']}")
        self.stdout.write(f"Manifest target: {result['manifest_path']}")
        if options.get("apply") and result.get("backup_path"):
            self.stdout.write(f"Backup manifest: {result['backup_path']}")
        if not options.get("apply"):
            self.stdout.write("Belum ada file yang diubah. Tambahkan --apply untuk menerapkan.")
