from django.core.management.base import BaseCommand

from aggregate.models import SurveyAccess
from surnasdes26.services.registry import enabled_surveys


class Command(BaseCommand):
    help = "Menyinkronkan survei enabled dari registry ke tabel kontrol akses."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        for manifest in enabled_surveys():
            _, created = SurveyAccess.objects.update_or_create(
                code=manifest["code"],
                defaults={"name": manifest["name"], "active": True},
            )
            created_count += int(created)
            updated_count += int(not created)
        self.stdout.write(self.style.SUCCESS("Sinkronisasi akses survei: OK"))
        self.stdout.write(f"Dibuat: {created_count}")
        self.stdout.write(f"Diperbarui: {updated_count}")
