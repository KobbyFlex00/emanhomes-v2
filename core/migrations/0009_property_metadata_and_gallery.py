from django.db import migrations, models
import django.db.models.deletion


def populate_reference_numbers(apps, schema_editor):
    Property = apps.get_model('core', 'Property')
    for index, property_obj in enumerate(Property.objects.filter(reference_number='').order_by('id'), start=1):
        property_obj.reference_number = f'EH-{property_obj.id:06d}'
        property_obj.save(update_fields=('reference_number',))


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0008_remove_teammember_image_property_bathrooms_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='amenities',
            field=models.TextField(blank=True, help_text='One amenity per line'),
        ),
        migrations.AddField(
            model_name='property',
            name='is_featured',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='property',
            name='property_size',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='property',
            name='property_size_unit',
            field=models.CharField(blank=True, default='sq ft', max_length=20),
        ),
        migrations.AddField(
            model_name='property',
            name='reference_number',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.RunPython(
            populate_reference_numbers,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='property',
            name='reference_number',
            field=models.CharField(blank=True, max_length=30, unique=True),
        ),
        migrations.CreateModel(
            name='PropertyImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='properties/gallery/')),
                ('caption', models.CharField(blank=True, max_length=200)),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gallery', to='core.property')),
            ],
            options={'ordering': ('display_order', 'id')},
        ),
    ]
