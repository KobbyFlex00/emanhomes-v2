"""schema.org data for search engines, built only from confirmed company records."""
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse

SOCIAL_FIELDS = ('facebook', 'instagram', 'tiktok', 'twitter', 'linkedin', 'youtube', 'linktree')
WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def _absolute(path):
    return path if path.startswith('http') else f'{settings.SITE_URL}{path}'


def organization(config):
    """The business as a RealEstateAgent (a schema.org LocalBusiness)."""
    data = {
        '@context': 'https://schema.org',
        '@type': 'RealEstateAgent',
        'name': 'Eman Homes Limited GH',
        'url': settings.SITE_URL + '/',
        'logo': _absolute(static('img/logo.jpeg')),
        'image': _absolute(static('img/logo.jpeg')),
    }
    if not config:
        return data
    data.update({
        'telephone': config.main_phone,
        'email': config.email,
        'address': {'@type': 'PostalAddress', 'streetAddress': config.address, 'addressCountry': 'GH'},
    })
    if '24 hours' in (config.business_hours or '').lower():
        data['openingHoursSpecification'] = {
            '@type': 'OpeningHoursSpecification', 'dayOfWeek': WEEK, 'opens': '00:00', 'closes': '23:59',
        }
    same_as = [getattr(config, field) for field in SOCIAL_FIELDS if getattr(config, field)]
    if same_as:
        data['sameAs'] = same_as
    return data


def property_breadcrumbs(listing):
    trail = [('Home', reverse('home')), ('Properties', reverse('properties_list'))]
    if listing.category == 'land':
        trail.append(('Land', reverse('properties_land')))
    elif listing.category == 'residential':
        trail.append(('Houses', reverse('properties_houses')))
    trail.append((listing.title, reverse('property_detail', args=[listing.slug])))
    return {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': position, 'name': name, 'item': _absolute(path)}
            for position, (name, path) in enumerate(trail, start=1)
        ],
    }
