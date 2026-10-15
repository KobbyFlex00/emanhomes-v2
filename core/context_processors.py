from django.conf import settings

from .models import SiteConfiguration


def site_configuration(request):
    """
    Retrieves the first SiteConfiguration object found in the database.
    If none exists, it returns None (preventing a crash).
    """
    try:

        config = SiteConfiguration.objects.first()
    except Exception:
        config = None

    return {
        'site_config': config,
        'analytics_measurement_id': getattr(settings, 'ANALYTICS_MEASUREMENT_ID', ''),
    }
