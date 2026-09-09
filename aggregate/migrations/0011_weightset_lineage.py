from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("aggregate", "0010_metadata_onboarding_report")]

    operations = [
        migrations.AddField(
            model_name="surveyweightset",
            name="parent_weight_set",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reused_versions",
                to="aggregate.surveyweightset",
            ),
        ),
    ]
