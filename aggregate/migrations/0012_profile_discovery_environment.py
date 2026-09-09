from django.db import migrations, models

import aggregate.models


class Migration(migrations.Migration):
    dependencies = [("aggregate", "0011_weightset_lineage")]

    operations = [
        migrations.AddField(
            model_name="surveyconnectionprofile",
            name="discovery_environment_prefix",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Prefix kredensial read-only untuk Source Catalog. Jika kosong, catalog "
                    "memakai environment prefix runtime."
                ),
                max_length=64,
                validators=[aggregate.models.ENV_PREFIX_VALIDATOR],
            ),
        ),
    ]
