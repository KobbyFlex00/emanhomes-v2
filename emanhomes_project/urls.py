"""
URL configuration for emanhomes_project project.
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from core.views import home, property_detail, contact, about, properties_list

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('about/', about, name='about'),
    path('properties/', properties_list, name='properties_list'),
    path('property/<slug:slug>/', property_detail, name='property_detail'),
    path('contact/', contact, name='contact'),
]

# This ensures media files work correctly in debug mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)