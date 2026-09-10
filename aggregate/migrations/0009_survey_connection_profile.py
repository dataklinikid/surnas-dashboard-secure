import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


def seed_connection_profiles(apps, schema_editor):
    SurveyConnectionProfile = apps.get_model("aggregate", "SurveyConnectionProfile")
    SurveyDataSource = apps.get_model("aggregate", "SurveyDataSource")

    for source in SurveyDataSource.objects.order_by("pk"):
        profile, _ = SurveyConnectionProfile.objects.get_or_create(
            code=source.connection_alias,
            defaults={
                "name": source.connection_alias.replace("_", " ").title(),
                "engine": source.engine,
                "environment_prefix": source.environment_prefix,
                "description": "Dibentuk otomatis dari data source yang sudah tersedia.",
                "active": True,
            },
        )
        source.connection_profile = profile
        source.save(update_fields=("connection_profile",))


class Migration(migrations.Migration):
    dependencies = [("aggregate", "0008_event_type_and_modules")]

    operations = [
        migrations.CreateModel(
            name="SurveyConnectionProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=64, unique=True, validators=[django.core.validators.RegexValidator(message="Kode harus diawali huruf kecil dan hanya berisi huruf kecil, angka, atau underscore.", regex="^[a-z][a-z0-9_]{2,63}$")])),
                ("name", models.CharField(max_length=160)),
                ("engine", models.CharField(choices=[("mariadb", "MariaDB/MySQL")], default="mariadb", max_length=16)),
                ("environment_prefix", models.CharField(help_text="Prefix environment variable; tidak menyimpan host, user, atau password.", max_length=64, validators=[django.core.validators.RegexValidator(message="Environment prefix hanya boleh berisi huruf kapital, angka, atau underscore.", regex="^[A-Z][A-Z0-9_]{2,63}$")])),
                ("description", models.TextField(blank=True)),
                ("active", models.BooleanField(default=True)),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.AddField(
            model_name="surveydatasource",
            name="connection_profile",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="data_sources", to="aggregate.surveyconnectionprofile"),
        ),
        migrations.RunPython(seed_connection_profiles, migrations.RunPython.noop),
    ]
