from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("aggregate", "0005_dynamic_survey_foundation"),
    ]

    operations = [
        migrations.AddField(
            model_name="surveyaccess",
            name="dashboard_config",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="surveyaccess",
            name="privacy_config",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
