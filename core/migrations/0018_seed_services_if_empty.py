from django.db import migrations

# The services Eman Homes offers, as listed in the website specification (PRD section 2).
# Seeded only when no services exist, so anything staff already entered is untouched.
SERVICES = [
    ('Land sales', 'fas fa-map-location-dot',
     'Plots and land for residential and commercial use. Ask us about location, size, '
     'documentation and the steps to purchase.'),
    ('House sales', 'fas fa-house',
     'Houses and residential property for sale. Browse current listings or tell us what you are looking for.'),
    ('Property development', 'fas fa-city',
     'Residential and commercial development projects. Speak to us about current and upcoming developments.'),
    ('Rentals and leasing', 'fas fa-key',
     'Residential and commercial property to rent or lease. Tell us your budget, preferred area and timing.'),
    ('Construction', 'fas fa-helmet-safety',
     'Construction services for homes and commercial buildings. Contact us to discuss your project.'),
    ('Property refurbishment', 'fas fa-paint-roller',
     'Renovation and refurbishment of existing properties. Share what you want to improve and we will advise.'),
]


def seed_services(apps, schema_editor):
    Service = apps.get_model('core', 'Service')
    if Service.objects.exists():
        return
    for order, (title, icon, description) in enumerate(SERVICES, start=1):
        Service.objects.create(title=title, icon_name=icon, description=description, display_order=order)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_service_order_and_visibility'),
    ]

    operations = [
        migrations.RunPython(seed_services, migrations.RunPython.noop),
    ]
