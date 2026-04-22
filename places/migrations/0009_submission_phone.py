# Generated migration to add phone field to Submission model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('places', '0008_candidate_source_channel_spot_last_confirmed_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='phone',
            field=models.CharField(blank=True, max_length=15),
        ),
    ]
