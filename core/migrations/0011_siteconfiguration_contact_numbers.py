from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0010_contactmessage_lead_operations'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='secondary_phone',
            field=models.CharField(default='+233 55 448 0444', max_length=50),
        ),
        migrations.AddField(
            model_name='siteconfiguration',
            name='whatsapp_phone',
            field=models.CharField(default='+233 20 584 3775', max_length=50),
        ),
    ]
