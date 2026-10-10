from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0009_property_metadata_and_gallery'),
    ]

    operations = [
        migrations.AddField(
            model_name='contactmessage',
            name='follow_up_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='contactmessage',
            name='internal_notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='contactmessage',
            name='lead_status',
            field=models.CharField(
                choices=[
                    ('new', 'New'),
                    ('in_progress', 'In progress'),
                    ('qualified', 'Qualified'),
                    ('closed', 'Closed'),
                ],
                default='new',
                max_length=20,
            ),
        ),
    ]
