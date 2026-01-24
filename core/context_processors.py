from .models import SiteConfiguration

def site_configuration(request):
    try:
        config = SiteConfiguration.objects.first()
    except:
        config = None
    return {'site_config': config}