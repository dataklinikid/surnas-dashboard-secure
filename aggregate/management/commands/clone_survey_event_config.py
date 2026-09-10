from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from aggregate.models import (
    LOWER_CODE_VALIDATOR,
    SurveyAccess,
    SurveyDataSource,
    SurveyEventModule,
)
from surnasdes26.services.registry import load_registry


class Command(BaseCommand):
    help = (
        "Membuat kerangka draft event PostgreSQL-only tanpa menyalin metadata, konfigurasi "
        "dashboard, atau konfigurasi modul dari event lain. Default hanya preview."
    )

    def add_arguments(self, parser):
        parser.add_argument("--source", required=True)
        parser.add_argument("--target", required=True)
        parser.add_argument("--name", required=True)
        parser.add_argument("--database-name", required=True)
        parser.add_argument("--target-n", type=int)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        source_code = options["source"].strip().lower()
        target_code = options["target"].strip().lower()
        target_name = options["name"].strip()

        try:
            LOWER_CODE_VALIDATOR(target_code)
        except ValidationError as exc:
            raise CommandError(str(exc)) from exc
        if not target_name:
            raise CommandError("--name wajib diisi.")
        if source_code == target_code:
            raise CommandError("Kode source dan target tidak boleh sama.")
        if target_code in load_registry():
            raise CommandError("Target sudah memiliki manifest JSON; command ini khusus event PostgreSQL-only.")
        if SurveyAccess.objects.filter(code=target_code).exists():
            raise CommandError("Target event sudah tersedia di PostgreSQL.")

        try:
            source = SurveyAccess.objects.select_related(
                "program", "region", "data_source"
            ).get(
                code=source_code,
                active=True,
                status=SurveyAccess.Status.ACTIVE,
            )
        except SurveyAccess.DoesNotExist as exc:
            raise CommandError("Source event aktif dan lengkap tidak ditemukan.") from exc

        database_name = options["database_name"].strip()
        if database_name.casefold() == source.data_source.database_name.casefold():
            raise CommandError("--database-name harus berbeda dari database event source.")
        target_n = options.get("target_n")
        if target_n is None:
            target_n = source.data_source.target_n

        self.stdout.write(
            "Clone dynamic survey event: APPLY"
            if options["apply"]
            else "Clone dynamic survey event: PREVIEW"
        )
        self.stdout.write(f"Source: {source.code}")
        self.stdout.write(f"Target: {target_code}")
        self.stdout.write(f"Name: {target_name}")
        self.stdout.write(f"Event type: {source.event_type.code if source.event_type else '-'}")
        self.stdout.write(f"Program: {source.program.code if source.program else '-'}")
        self.stdout.write(f"Region: {source.region.code if source.region else '-'}")
        self.stdout.write(f"Database alias: {source.data_source.connection_alias}")
        self.stdout.write(f"Database name: {database_name}")
        self.stdout.write(f"Table: {source.data_source.table_name}")
        self.stdout.write(f"Target n: {target_n if target_n is not None else '-'}")
        self.stdout.write("Metadata: tidak disalin; wajib diunggah dari kuesioner target")
        self.stdout.write("Dashboard config: tidak disalin")
        self.stdout.write("Initial status: draft")
        self.stdout.write("Initial active: false")
        self.stdout.write("Manifest JSON: tidak dibuat")
        self.stdout.write("Membership: tidak dibuat")
        self.stdout.write("Weight set: tidak dibuat")
        self.stdout.write(
            f"Modules: {source.event_modules.filter(enabled=True).count()} pilihan disalin sebagai pending"
        )

        if not options["apply"]:
            self.stdout.write("Preview selesai; PostgreSQL belum diubah.")
            return

        with transaction.atomic():
            target = SurveyAccess.objects.create(
                code=target_code,
                name=target_name,
                event_type=source.event_type,
                program=source.program,
                region=source.region,
                period_start=source.period_start,
                period_end=source.period_end,
                dashboard_config={},
                privacy_config={"aggregate_only": True},
                status=SurveyAccess.Status.DRAFT,
                active=False,
            )
            source_config = source.data_source
            SurveyDataSource.objects.create(
                survey=target,
                connection_profile=source_config.connection_profile,
                engine=source_config.engine,
                connection_alias=source_config.connection_alias,
                environment_prefix=source_config.environment_prefix,
                database_name=database_name,
                table_name=source_config.table_name,
                identity_column=source_config.identity_column,
                latest_id_column=source_config.latest_id_column,
                valid_column=source_config.valid_column,
                valid_value=source_config.valid_value,
                target_n=target_n,
                active=True,
            )
            SurveyEventModule.objects.bulk_create(
                [
                    SurveyEventModule(
                        survey=target,
                        module=assignment.module,
                        enabled=assignment.enabled,
                        readiness=SurveyEventModule.Readiness.PENDING,
                        config={},
                    )
                    for assignment in source.event_modules.select_related("module")
                ]
            )

        self.stdout.write(self.style.SUCCESS("Clone dynamic survey event: APPLIED"))
        self.stdout.write("Event belum aktif; unggah metadata kuesioner target sebelum validasi.")
