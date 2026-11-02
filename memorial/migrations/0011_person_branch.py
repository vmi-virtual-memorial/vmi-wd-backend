# Additive: blank branch column used only as an admin override of the inferred branch.
# No data is written; see the backfill_branches management command for opt-in backfill.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('memorial', '0010_alter_conflict_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='branch',
            field=models.CharField(blank=True, choices=[('ARMY', 'U.S. Army'), ('ARMY_AIR', 'U.S. Army Air Forces'), ('AIR_FORCE', 'U.S. Air Force'), ('NAVY', 'U.S. Navy'), ('MARINES', 'U.S. Marine Corps'), ('COAST_GUARD', 'U.S. Coast Guard'), ('CSA', 'Confederate States Army'), ('ALLIED', 'Allied & Foreign Service'), ('CIVILIAN', 'Civilian'), ('CADET', 'VMI Corps of Cadets')], db_index=True, default='', help_text='Service branch. Leave blank to infer it from rank/unit; set it to override the inference.', max_length=12),
        ),
    ]
