from django.db import migrations, models


def seed_access(apps, schema_editor):
    SurveyAccess = apps.get_model("aggregate", "SurveyAccess")
    SurveyAccess.objects.update_or_create(
        code="surnasdes26",
        defaults={"name": "Surnas Desember 2026", "active": True},
    )


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="SurveyAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=120)),
                ("active", models.BooleanField(default=True)),
            ],
            options={
                "permissions": [
                    ("access_surnasdes26_monitoring", "Dapat melihat monitoring Surnas Desember 2026"),
                    ("access_surnasdes26_analysis", "Dapat melihat analisis Surnas Desember 2026"),
                    ("export_surnasdes26", "Dapat mengekspor data Surnas Desember 2026"),
                ]
            },
        ),
        migrations.RunPython(seed_access, migrations.RunPython.noop),
    ]
