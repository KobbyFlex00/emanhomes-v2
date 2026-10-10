from django.db import migrations, models


def add_currency_if_missing(apps, schema_editor):
    Property = apps.get_model('core', 'Property')
    field = models.CharField(
        choices=[('USD', 'USD ($)'), ('GHS', 'GHS (GH₵)')],
        default='USD',
        max_length=3,
    )
    field.set_attributes_from_name('currency')
    field.model = Property
    cursor = schema_editor.connection.cursor()
    column_names = {
        column.name for column in schema_editor.connection.introspection.get_table_description(
            cursor, Property._meta.db_table
        )
    }
    if field.column not in column_names:
        schema_editor.add_field(Property, field)


def remove_currency_if_present(apps, schema_editor):
    Property = apps.get_model('core', 'Property')
    field = models.CharField(
        choices=[('USD', 'USD ($)'), ('GHS', 'GHS (GH₵)')],
        default='USD',
        max_length=3,
    )
    field.set_attributes_from_name('currency')
    field.model = Property
    cursor = schema_editor.connection.cursor()
    column_names = {
        column.name for column in schema_editor.connection.introspection.get_table_description(
            cursor, Property._meta.db_table
        )
    }
    if field.column in column_names:
        schema_editor.remove_field(Property, field)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0006_contactmessage_lead_fields'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_currency_if_missing, remove_currency_if_present),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='property',
                    name='currency',
                    field=models.CharField(
                        choices=[('USD', 'USD ($)'), ('GHS', 'GHS (GH₵)')],
                        default='USD',
                        max_length=3,
                    ),
                ),
            ],
        ),
    ]
