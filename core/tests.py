from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import ContactForm
from .models import ContactMessage, Property


@override_settings(SECURE_SSL_REDIRECT=False)
class PropertySearchTests(TestCase):
    def setUp(self):
        Property.objects.create(
            title='Modern home in East Legon',
            category='residential',
            location='East Legon',
            description='A bright family home',
            price=250000,
            bedrooms=4,
        )
        Property.objects.create(
            title='Commercial plot',
            category='commercial',
            location='Airport City',
            description='Prime commercial opportunity',
            price=500000,
        )

    def test_search_matches_title_and_location(self):
        response = self.client.get(reverse('properties_list'), {'q': 'East Legon'})
        self.assertContains(response, 'Modern home in East Legon')
        self.assertNotContains(response, 'Commercial plot')

    def test_filters_and_paginates_results(self):
        response = self.client.get(reverse('properties_list'), {'category': 'residential', 'bedrooms': '3'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['properties'].paginator.count, 1)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SECURE_SSL_REDIRECT=False,
)
class ContactWorkflowTests(TestCase):
    def test_contact_form_requires_consent(self):
        form = ContactForm(data={
            'name': 'Ama', 'email': 'ama@example.com', 'subject': 'Help',
            'message': 'Please call me', 'inquiry_type': 'general',
            'preferred_contact': 'email',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('consent_to_contact', form.errors)

    def test_valid_contact_is_saved_and_notified(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Ama',
            'email': 'ama@example.com',
            'subject': 'Viewing',
            'message': 'I would like to view a house.',
            'inquiry_type': 'viewing',
            'preferred_contact': 'whatsapp',
            'consent_to_contact': 'on',
        })
        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Ama', mail.outbox[0].body)

    def test_property_inquiry_links_to_property(self):
        property_obj = Property.objects.create(
            title='East Legon Hills land',
            category='land',
            location='East Legon Hills',
            description='Residential land',
            price=100000,
        )
        response = self.client.post(f'{reverse("contact")}?property={property_obj.slug}', {
            'name': 'Kojo',
            'email': 'kojo@example.com',
            'subject': 'Viewing',
            'message': 'I would like to arrange a viewing.',
            'inquiry_type': 'property',
            'preferred_contact': 'phone',
            'consent_to_contact': 'on',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactMessage.objects.get().property, property_obj)

    def test_oversized_source_is_trimmed(self):
        response = self.client.post(reverse('contact'), {
            'name': 'Esi',
            'email': 'esi@example.com',
            'subject': 'Hello',
            'message': 'Please contact me.',
            'inquiry_type': 'general',
            'preferred_contact': 'email',
            'consent_to_contact': 'on',
            'source': 'x' * 500,
        })
        self.assertRedirects(response, reverse('contact'))
        self.assertEqual(len(ContactMessage.objects.get().source), 100)

    def test_missing_source_defaults_to_website(self):
        self.client.post(reverse('contact'), {
            'name': 'Yaw',
            'email': 'yaw@example.com',
            'subject': 'Hello',
            'message': 'Please contact me.',
            'inquiry_type': 'general',
            'preferred_contact': 'email',
            'consent_to_contact': 'on',
        })
        self.assertEqual(ContactMessage.objects.get().source, 'website')


class MediaStorageSettingsTests(TestCase):
    """Settings are evaluated at import, so exercise them in a fresh interpreter."""

    def _load_settings(self, **env):
        import os
        import subprocess
        import sys
        child_env = {k: v for k, v in os.environ.items() if k not in ('RENDER', 'CLOUDINARY_URL')}
        child_env.update(SECRET_KEY='test', DJANGO_SETTINGS_MODULE='emanhomes_project.settings', **env)
        return subprocess.run(
            [sys.executable, '-c',
             'import django; django.setup(); from django.conf import settings; '
             'print(settings.STORAGES["default"]["BACKEND"])'],
            env=child_env, capture_output=True, text=True,
        )

    def test_uses_filesystem_without_cloudinary_locally(self):
        result = self._load_settings()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('FileSystemStorage', result.stdout)

    def test_uses_cloudinary_when_configured(self):
        result = self._load_settings(CLOUDINARY_URL='cloudinary://key:secret@demo')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('MediaCloudinaryStorage', result.stdout)

    def test_render_refuses_to_start_without_cloudinary(self):
        result = self._load_settings(RENDER='true')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('CLOUDINARY_URL must be set on Render', result.stderr)


@override_settings(SECURE_SSL_REDIRECT=False)
class SeoEndpointTests(TestCase):
    def test_sitemap_lists_properties(self):
        property_obj = Property.objects.create(
            title='Sitemap test plot', category='land', location='Oyarifa',
            description='Plot', price=1000,
        )
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('property_detail', kwargs={'slug': property_obj.slug}))

    def test_robots_points_to_sitemap(self):
        response = self.client.get('/robots.txt')
        self.assertContains(response, 'Sitemap: ')


class BuildCommandTests(TestCase):
    def test_render_collectstatic_command_runs(self):
        from django.core.management import call_command
        call_command('collectstatic', interactive=False, dry_run=True, upload_unhashed_files=True, verbosity=0)
