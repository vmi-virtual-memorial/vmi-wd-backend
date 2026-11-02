# State-only: records the Conflict.Meta.ordering change made in 1b7d644 (no SQL).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('memorial', '0009_person_class_letter_two_chars'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='conflict',
            options={'ordering': ['order', '-start_year']},
        ),
    ]
