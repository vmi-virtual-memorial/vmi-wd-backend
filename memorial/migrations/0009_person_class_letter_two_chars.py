from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("memorial", "0008_seed_awards"),
    ]

    operations = [
        migrations.AlterField(
            model_name="person",
            name="class_letter",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Optional one- or two-letter suffix for class year (e.g., 'M' for 1956M, 'MS' for 1956MS)",
                max_length=2,
            ),
        ),
    ]
