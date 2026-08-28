from django.db import migrations


PERMISSION_NAMES = {
    "access_surnasdes26_monitoring": "Dapat melihat monitoring Surnas Februari 2026",
    "access_surnasdes26_analysis": "Dapat melihat analisis Surnas Februari 2026",
    "export_surnasdes26": "Dapat mengekspor data Surnas Februari 2026",
}


def update_labels(apps, schema_editor):
    SurveyAccess = apps.get_model("aggregate", "SurveyAccess")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    SurveyAccess.objects.filter(code="surnasdes26").update(name="Surnas Februari 2026")
    content_type = ContentType.objects.filter(app_label="aggregate", model="surveyaccess").first()
    if content_type:
        for codename, name in PERMISSION_NAMES.items():
            Permission.objects.filter(content_type=content_type, codename=codename).update(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("aggregate", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="surveyaccess",
            options={"permissions": list(PERMISSION_NAMES.items())},
        ),
        migrations.RunPython(update_labels, migrations.RunPython.noop),
    ]
