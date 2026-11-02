# Additive: one blank, unindexed column used only as an admin override of the inferred
# branch (filtering happens on the effective branch in Python, so no index).
# No data is written; the read-only branch_report command lists people to triage by hand.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('memorial', '0010_alter_conflict_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='branch',
            field=models.CharField(blank=True, choices=[('ARMY', 'U.S. Army'), ('ARMY_AIR', 'U.S. Army Air Forces'), ('AIR_FORCE', 'U.S. Air Force'), ('NAVY', 'U.S. Navy'), ('MARINES', 'U.S. Marine Corps'), ('COAST_GUARD', 'U.S. Coast Guard'), ('CSA', 'Confederate States Army'), ('ALLIED', 'Allied & Foreign Service'), ('CIVILIAN', 'Civilian'), ('CADET', 'VMI Corps of Cadets')], default='', help_text='Service branch. Leave blank to infer it from rank/unit; set it to override the inference.', max_length=12),
        ),
    ]
