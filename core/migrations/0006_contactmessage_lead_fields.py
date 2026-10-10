from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0005_contactmessage_alter_siteconfiguration_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contactmessage',
            name='consent_to_contact',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='contactmessage',
            name='inquiry_type',
            field=models.CharField(
                choices=[
                    ('general', 'General enquiry'),
                    ('property', 'Property enquiry'),
                    ('viewing', 'Request a viewing'),
                    ('listing', 'List or sell a property'),
                ],
                default='general',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='contactmessage',
            name='preferred_contact',
            field=models.CharField(
                choices=[('whatsapp', 'WhatsApp'), ('phone', 'Phone'), ('email', 'Email')],
                default='email',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='contactmessage',
            name='source',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='contactmessage',
            name='property',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='inquiries',
                to='core.property',
            ),
        ),
    ]
