from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


ROLE_PERMISSIONS = {
    "surnasdes26_monitor": ["access_surnasdes26_monitoring"],
    "surnasdes26_analyst": ["access_surnasdes26_monitoring", "access_surnasdes26_analysis"],
    "surnasdes26_admin": [
        "access_surnasdes26_monitoring",
        "access_surnasdes26_analysis",
        "export_surnasdes26",
    ],
}


class Command(BaseCommand):
    help = "Membuat atau memperbarui Group dan Permission Surnas Februari 2026."

    def handle(self, *args, **options):
        for group_name, codenames in ROLE_PERMISSIONS.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            permissions = Permission.objects.filter(content_type__app_label="aggregate", codename__in=codenames)
            if permissions.count() != len(codenames):
                raise RuntimeError("Permission belum lengkap. Jalankan migrate terlebih dahulu.")
            group.permissions.set(permissions)
            self.stdout.write(self.style.SUCCESS(f"Role {group_name} siap."))
