from django.db import migrations

# Official profiles from the Eman Homes specification (PRD section 11).
# Only empty fields are filled; anything staff already entered is kept.
OFFICIAL_LINKS = {
    'twitter': 'https://x.com/eman_homes',
    'linkedin': 'https://www.linkedin.com/in/eman-homes',
}


def fill_empty_social_links(apps, schema_editor):
    SiteConfiguration = apps.get_model('core', 'SiteConfiguration')
    for config in SiteConfiguration.objects.all():
        changed = []
        for field, url in OFFICIAL_LINKS.items():
            if not getattr(config, field):
                setattr(config, field, url)
                changed.append(field)
        if changed:
            config.save(update_fields=changed)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_phase2_publication_seo_enquiry_fields'),
    ]

    operations = [
        migrations.RunPython(fill_empty_social_links, migrations.RunPython.noop),
    ]
