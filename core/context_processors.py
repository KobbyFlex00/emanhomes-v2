from django.conf import settings

from .models import LegalPage, SiteConfiguration


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
    except Exception:
        config = None
        published_legal = set()

    return {
        'site_config': config,
        'privacy_published': LegalPage.PRIVACY in published_legal,
        'terms_published': LegalPage.TERMS in published_legal,
        'analytics_measurement_id': getattr(settings, 'ANALYTICS_MEASUREMENT_ID', ''),
    }
