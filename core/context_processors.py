from django.conf import settings

from .models import LegalPage, Property, SiteConfiguration


def site_configuration(request):
    """
    Retrieves the first SiteConfiguration object found in the database.
    If none exists, it returns None (preventing a crash).
    """
    try:
        config = SiteConfiguration.objects.first()
        published_legal = set(
            LegalPage.objects.filter(status=LegalPage.PUBLISHED).values_list('slug', flat=True)
        )
        # The PRD shows Rentals only when there are real rental listings.
        has_rentals = Property.objects.public().filter(status='for_rent').exists()
    except Exception:
        config = None
        published_legal = set()
        has_rentals = False

    host = request.get_host() if request is not None else ''
    return {
        'site_config': config,
        'site_url': settings.SITE_URL,
        # Staging and the raw Render address must never be indexed.
        'site_noindex': settings.SITE_NOINDEX or host.endswith('.onrender.com'),
        'privacy_published': LegalPage.PRIVACY in published_legal,
        'terms_published': LegalPage.TERMS in published_legal,
        'has_rentals': has_rentals,
        'analytics_measurement_id': getattr(settings, 'ANALYTICS_MEASUREMENT_ID', ''),
    }
