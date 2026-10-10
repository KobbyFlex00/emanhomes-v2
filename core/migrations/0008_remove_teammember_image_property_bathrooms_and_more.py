from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0007_property_currency'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='teammember',
            name='image',
        ),
        migrations.AddField(
            model_name='property',
            name='bathrooms',
            field=models.IntegerField(default=0, help_text='Number of bathrooms'),
        ),
        migrations.AddField(
            model_name='property',
            name='bedrooms',
            field=models.IntegerField(default=0, help_text='Number of bedrooms'),
        ),
        migrations.AddField(
            model_name='teammember',
            name='image_url',
            field=models.URLField(
                blank=True,
                help_text="Paste a direct link to a .jpg/.png photo (e.g., Right-click LinkedIn photo > Copy Image Address). Google Drive 'view' links will NOT work.",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='property',
            name='main_image',
            field=models.ImageField(blank=True, null=True, upload_to='properties/'),
        ),
    ]
