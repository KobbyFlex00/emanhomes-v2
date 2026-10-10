from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0006_contactmessage_lead_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='currency',
            field=models.CharField(
                choices=[('USD', 'USD ($)'), ('GHS', 'GHS (GH₵)')],
                default='USD',
                max_length=3,
            ),
        ),
    ]
