from django.db import migrations, models


def table_columns(schema_editor, model):
    cursor = schema_editor.connection.cursor()
    return {
        column.name for column in schema_editor.connection.introspection.get_table_description(
            cursor, model._meta.db_table
        )
    }


def reconcile_legacy_property_fields(apps, schema_editor):
    Property = apps.get_model('core', 'Property')
    TeamMember = apps.get_model('core', 'TeamMember')
    property_columns = table_columns(schema_editor, Property)
    team_columns = table_columns(schema_editor, TeamMember)

    if 'image' in team_columns:
        schema_editor.remove_field(TeamMember, TeamMember._meta.get_field('image'))

    for name, field in (
        ('bedrooms', models.IntegerField(default=0, help_text='Number of bedrooms')),
        ('bathrooms', models.IntegerField(default=0, help_text='Number of bathrooms')),
    ):
        field.set_attributes_from_name(name)
        if name not in property_columns:
            field.model = Property
            schema_editor.add_field(Property, field)

    if 'image_url' not in team_columns:
        field = models.URLField(blank=True, null=True)
        field.set_attributes_from_name('image_url')
        field.model = TeamMember
        schema_editor.add_field(TeamMember, field)

    if 'main_image' in property_columns:
        old_field = Property._meta.get_field('main_image')
        new_field = models.ImageField(blank=True, null=True, upload_to='properties/')
        new_field.set_attributes_from_name('main_image')
        schema_editor.alter_field(Property, old_field, new_field)


def reverse_legacy_property_fields(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0007_property_currency'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(reconcile_legacy_property_fields, reverse_legacy_property_fields),
            ],
            state_operations=[
                migrations.RemoveField(model_name='teammember', name='image'),
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
            ],
        ),
    ]
