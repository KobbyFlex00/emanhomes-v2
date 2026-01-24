from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from core.views import home, property_detail, client_portal, contact, about

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('property/<slug:slug>/', property_detail, name='property_detail'),
    path('about/', about, name='about'),
    path('contact/', contact, name='contact'),
    path('portal/', client_portal, name='client_portal'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)