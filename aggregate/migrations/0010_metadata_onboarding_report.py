from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("aggregate", "0009_survey_connection_profile")]

    operations = [
        migrations.AddField(
            model_name="surveymetadataversion",
            name="onboarding_report",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
