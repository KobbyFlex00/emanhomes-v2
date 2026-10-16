"""
URL configuration for emanhomes_project project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps import Sitemap
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import path, reverse

from core.models import LegalPage, Property
from core.views import (
    about,
    contact,
    enquiry_thanks,
    health_check,
    home,
    legal_page,
    properties_list,
    property_detail,
    services,
)


class StaticSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        items = ['home', 'about', 'services', 'properties_list', 'properties_land', 'properties_houses', 'contact']
        if Property.objects.public().filter(status='for_rent').exists():
            items.append('properties_rentals')
        return items

    def location(self, item):
        return reverse(item)


class LegalSitemap(Sitemap):
    priority = 0.3
    changefreq = 'yearly'

    def items(self):
        return LegalPage.objects.filter(status=LegalPage.PUBLISHED)

    def lastmod(self, item):
        return item.updated_at

    def location(self, item):
        return reverse(item.slug)  # URL names match the slugs: 'privacy', 'terms'


class PropertySitemap(Sitemap):
    changefreq = 'daily'
    priority = 0.9

    def items(self):
        return Property.objects.public().order_by('-created_at', 'pk')

    def lastmod(self, item):
        return item.updated_at

    def location(self, item):
        return reverse('property_detail', kwargs={'slug': item.slug})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('healthz/', health_check, name='health_check'),
    path('', home, name='home'),
    path('about/', about, name='about'),
    path('properties/', properties_list, name='properties_list'),
    path('properties/land/', properties_list, {'collection': 'land'}, name='properties_land'),
    path('properties/houses/', properties_list, {'collection': 'houses'}, name='properties_houses'),
    path('properties/rentals/', properties_list, {'collection': 'rentals'}, name='properties_rentals'),
    path('services/', services, name='services'),
    path('property/<slug:slug>/', property_detail, name='property_detail'),
    path('contact/', contact, name='contact'),
    path('contact/thank-you/', enquiry_thanks, name='enquiry_thanks'),
    path('privacy/', legal_page, {'slug': 'privacy'}, name='privacy'),
    path('terms/', legal_page, {'slug': 'terms'}, name='terms'),
    path('sitemap.xml', sitemap, {'sitemaps': {'static': StaticSitemap, 'properties': PropertySitemap, 'legal': LegalSitemap}}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', lambda request: HttpResponse(
        f"User-agent: *\nAllow: /\nSitemap: {request.build_absolute_uri(reverse('django.contrib.sitemaps.views.sitemap'))}\n",
        content_type='text/plain'
    )),
]

# This ensures media files work correctly in debug mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
