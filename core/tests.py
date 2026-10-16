import importlib
import re
import smtplib
import time
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import ContactForm
from .models import ContactMessage, LegalPage, Property, Service, SiteConfiguration


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
@override_settings(ENQUIRY_RATE_LIMIT=(1000, 600))
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
            'phone': '+233 20 584 0000',
            'consent_to_contact': 'on',
        })
        self.assertRedirects(response, reverse('enquiry_thanks'))
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
            'phone': '+233 20 584 0000',
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
            'phone': '+233 20 584 0000',
            'consent_to_contact': 'on',
            'source': 'x' * 500,
        })
        self.assertRedirects(response, reverse('enquiry_thanks'))
        self.assertEqual(len(ContactMessage.objects.get().source), 100)

    def test_missing_source_defaults_to_website(self):
        self.client.post(reverse('contact'), {
            'name': 'Yaw',
            'email': 'yaw@example.com',
            'subject': 'Hello',
            'message': 'Please contact me.',
            'inquiry_type': 'general',
            'preferred_contact': 'email',
            'phone': '+233 20 584 0000',
            'consent_to_contact': 'on',
        })
        self.assertEqual(ContactMessage.objects.get().source, 'website')


class MediaStorageSettingsTests(TestCase):
    """Settings are evaluated at import, so exercise them in a fresh interpreter."""

    def _load_settings(self, **env):
        import os
        import subprocess
        import sys
        child_env = {k: v for k, v in os.environ.items() if k not in ('RENDER', 'CLOUDINARY_URL', 'DEBUG')}
        child_env.update(SECRET_KEY='test', DJANGO_SETTINGS_MODULE='emanhomes_project.settings', **env)
        return subprocess.run(
            [sys.executable, '-c',
             'import django; django.setup(); from django.conf import settings; '
             'print(settings.STORAGES["default"]["BACKEND"], settings.DEBUG, settings.SECURE_SSL_REDIRECT)'],
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

    def test_debug_defaults_off_with_https_redirect(self):
        result = self._load_settings()
        self.assertTrue(result.stdout.strip().endswith('False True'), result.stdout)

    def test_debug_env_relaxes_https_for_local_development(self):
        result = self._load_settings(DEBUG='true')
        self.assertTrue(result.stdout.strip().endswith('True False'), result.stdout)

    def test_debug_is_refused_on_render(self):
        result = self._load_settings(DEBUG='true', RENDER='true', CLOUDINARY_URL='cloudinary://k:s@demo')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DEBUG must not be enabled on Render', result.stderr)


@override_settings(SECURE_SSL_REDIRECT=True)
class HealthCheckTests(TestCase):
    def test_health_check_reports_ok_over_plain_http(self):
        response = self.client.get(reverse('health_check'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})
        self.assertIn('no-cache', response['Cache-Control'])

    def test_health_check_rejects_post(self):
        self.assertEqual(self.client.post(reverse('health_check')).status_code, 405)

    def test_other_pages_still_redirect_to_https(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 301)


@override_settings(SECURE_SSL_REDIRECT=False)
class ErrorPageTests(TestCase):
    def test_unknown_url_uses_branded_404(self):
        response = self.client.get('/no-such-page/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
        self.assertContains(response, 'Browse properties', status_code=404)

    def test_missing_property_returns_404(self):
        response = self.client.get(reverse('property_detail', kwargs={'slug': 'does-not-exist'}))
        self.assertEqual(response.status_code, 404)

    def test_500_template_renders_without_request_context(self):
        from django.template.loader import render_to_string
        html = render_to_string('500.html')
        self.assertIn('Something went wrong', html)



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
        self.assertContains(response, 'Sitemap: http://testserver/sitemap.xml\n')


class BuildCommandTests(TestCase):
    def test_render_collectstatic_command_runs(self):
        from django.core.management import call_command
        call_command('collectstatic', interactive=False, dry_run=True, upload_unhashed_files=True, verbosity=0)


class RenderHostnameTests(TestCase):
    def test_render_hostname_is_allowed(self):
        import os
        import subprocess
        import sys
        env = {k: v for k, v in os.environ.items() if k not in ('RENDER', 'CLOUDINARY_URL')}
        env.update(
            SECRET_KEY='test', DJANGO_SETTINGS_MODULE='emanhomes_project.settings',
            RENDER_EXTERNAL_HOSTNAME='eman-homes-staging.onrender.com',
        )
        result = subprocess.run(
            [sys.executable, '-c',
             'import django; django.setup(); from django.conf import settings; '
             'print(settings.ALLOWED_HOSTS, settings.CSRF_TRUSTED_ORIGINS)'],
            env=env, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("'eman-homes-staging.onrender.com'", result.stdout)
        self.assertIn("'https://eman-homes-staging.onrender.com'", result.stdout)


@override_settings(SECURE_SSL_REDIRECT=False)
class BusinessHoursTests(TestCase):
    def test_footer_shows_round_the_clock_hours(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Open 24 hours')
        self.assertNotContains(response, 'Closed')


# --- Phase 2: publication, pricing, enquiries, roles ---------------------------------





class FailingEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise smtplib.SMTPException('SMTP server unavailable')


def make_property(**overrides):
    fields = {
        'title': 'Three bedroom house in Oyarifa',
        'category': 'residential',
        'location': 'Oyarifa',
        'description': 'Family home',
        'price': Decimal('250000'),
        'video_url': 'https://www.instagram.com/reel/ABC123/',
    }
    fields.update(overrides)
    return Property.objects.create(**fields)


ENQUIRY = {
    'name': 'Ama Mensah',
    'email': 'ama@example.com',
    'phone': '+233 24 000 0000',
    'subject': 'Viewing',
    'message': 'I would like to view this property.',
    'inquiry_type': 'property',
    'preferred_contact': 'whatsapp',
    'consent_to_contact': 'on',
}


@override_settings(SECURE_SSL_REDIRECT=False)
@override_settings(ENQUIRY_RATE_LIMIT=(1000, 600))
class PublicationVisibilityTests(TestCase):
    def setUp(self):
        self.published = make_property(title='Published plot', category='land')
        self.draft = make_property(title='Draft plot', category='land', publication_status=Property.DRAFT)
        self.archived = make_property(title='Archived plot', category='land', publication_status=Property.ARCHIVED)

    def test_listing_page_shows_only_published(self):
        response = self.client.get(reverse('properties_list'))
        self.assertContains(response, 'Published plot')
        self.assertNotContains(response, 'Draft plot')
        self.assertNotContains(response, 'Archived plot')

    def test_home_shows_only_published(self):
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, 'Draft plot')
        land = next(c for c in response.context['categories'] if c['key'] == 'land')
        self.assertEqual(land['count'], 1)

    def test_hidden_listing_detail_returns_404(self):
        for hidden in (self.draft, self.archived):
            response = self.client.get(reverse('property_detail', args=[hidden.slug]))
            self.assertEqual(response.status_code, 404)

    def test_sitemap_excludes_hidden_listings(self):
        response = self.client.get('/sitemap.xml')
        self.assertContains(response, self.published.slug)
        self.assertNotContains(response, self.draft.slug)
        self.assertNotContains(response, self.archived.slug)

    def test_enquiry_cannot_be_linked_to_hidden_listing(self):
        self.client.post(f"{reverse('contact')}?property={self.draft.slug}", ENQUIRY)
        self.assertIsNone(ContactMessage.objects.get().property)

    def test_sold_listing_stays_visible_marked_sold_after_available(self):
        Property.objects.all().delete()
        make_property(title='Sold house', status='sold', is_featured=True)
        make_property(title='Available house')
        response = self.client.get(reverse('properties_list'))
        titles = [p.title for p in response.context['properties']]
        self.assertEqual(titles, ['Available house', 'Sold house'])
        self.assertContains(response, '>Sold<')

    def test_sold_listing_detail_is_public_without_calculator(self):
        sold = make_property(title='Sold villa', status='sold')
        response = self.client.get(reverse('property_detail', args=[sold.slug]))
        self.assertContains(response, 'Sold')
        self.assertNotContains(response, 'Payment Calculator')


@override_settings(SECURE_SSL_REDIRECT=False)
class PricingAndSearchTests(TestCase):
    def test_price_display_formats(self):
        self.assertEqual(make_property(price=Decimal('250000')).price_display, '$250,000')
        self.assertEqual(
            make_property(title='Rental', currency='GHS', price=Decimal('1500.50')).price_display,
            'GH₵1,500.50',
        )

    def test_contact_for_price_listing(self):
        listing = make_property(title='Price on request plot', price=None)
        self.assertContains(self.client.get(reverse('properties_list')), 'Contact for price')
        detail = self.client.get(reverse('property_detail', args=[listing.slug]))
        self.assertContains(detail, 'Contact for price')
        self.assertNotContains(detail, 'Payment Calculator')

    def test_malformed_filters_are_ignored_not_errors(self):
        make_property()
        for params in ({'min_price': 'abc'}, {'max_price': '1e999'}, {'bedrooms': 'x'}, {'min_price': '-5'}):
            response = self.client.get(reverse('properties_list'), params)
            self.assertEqual(response.status_code, 200, params)
            self.assertEqual(response.context['properties'].paginator.count, 1, params)

    def test_search_by_reference_number(self):
        listing = make_property()
        make_property(title='Unrelated plot', location='Kasoa', description='Other')
        response = self.client.get(reverse('properties_list'), {'q': listing.reference_number.lower()})
        self.assertEqual([p.pk for p in response.context['properties']], [listing.pk])

    def test_unusual_filter_values_do_not_error(self):
        make_property()
        for params in ({'bedrooms': '\u00b2'}, {'bedrooms': '9' * 5000}, {'min_price': '1e100'}):
            response = self.client.get(reverse('properties_list'), params)
            self.assertEqual(response.status_code, 200, params)

    def test_huge_min_price_matches_nothing_rather_than_everything(self):
        make_property()
        response = self.client.get(reverse('properties_list'), {'min_price': '1e100'})
        self.assertEqual(response.context['properties'].paginator.count, 0)

    def test_duplicate_titles_get_unique_slugs(self):
        first = make_property(title='Plot in Aburi')
        second = make_property(title='Plot in Aburi')
        self.assertEqual(first.slug, 'plot-in-aburi')
        self.assertEqual(second.slug, 'plot-in-aburi-2')

    def test_negative_price_is_rejected(self):
        listing = Property(title='Bad', category='land', location='X', description='X',
                           price=Decimal('-1'), video_url='https://youtu.be/abc')
        with self.assertRaises(ValidationError):
            listing.full_clean()


class VideoEmbedTests(TestCase):
    def embed(self, url):
        return Property(video_url=url).get_embed_url()

    def test_supported_links(self):
        cases = {
            'https://www.youtube.com/watch?v=abc123&t=30s': 'https://www.youtube.com/embed/abc123',
            'https://youtu.be/abc123?si=x': 'https://www.youtube.com/embed/abc123',
            'https://www.youtube.com/shorts/abc123': 'https://www.youtube.com/embed/abc123',
            'https://www.instagram.com/reel/DZSjYCLsITq/?igsh=1': 'https://www.instagram.com/reel/DZSjYCLsITq/embed',
            'https://instagram.com/p/DZUED9ZjKEN': 'https://www.instagram.com/p/DZUED9ZjKEN/embed',
        }
        for url, expected in cases.items():
            self.assertEqual(self.embed(url), expected, url)

    def test_other_sites_are_never_embedded(self):
        for url in ('http://[broken/watch?v=1', 'https://evil.example/watch?v=1', 'https://youtube.com.evil.example/watch?v=1',
                    'javascript:alert(1)', 'https://www.youtube.com/'):
            self.assertIsNone(self.embed(url), url)

    def test_admin_validation_rejects_unsupported_video(self):
        listing = Property(title='X', category='land', location='X', description='X',
                           price=1, video_url='https://vimeo.com/123')
        with self.assertRaises(ValidationError) as ctx:
            listing.full_clean()
        self.assertIn('video_url', ctx.exception.message_dict)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', SECURE_SSL_REDIRECT=False)
@override_settings(ENQUIRY_RATE_LIMIT=(1000, 600))
class EnquiryPhase2Tests(TestCase):
    def test_phone_is_required_and_validated(self):
        for phone in ('', 'call me', '12', '+233 ' + '9' * 20):
            data = dict(ENQUIRY, phone=phone)
            response = self.client.post(reverse('contact'), data)
            self.assertEqual(response.status_code, 200, phone)
            self.assertIn('phone', response.context['form'].errors, phone)
        self.assertFalse(ContactMessage.objects.exists())

    def test_consent_must_be_given_explicitly(self):
        data = {k: v for k, v in ENQUIRY.items() if k != 'consent_to_contact'}
        response = self.client.post(reverse('contact'), data)
        self.assertContains(response, 'Please confirm we may contact you')
        self.assertFalse(ContactMessage.objects.exists())

    def test_property_page_form_requires_visible_consent(self):
        listing = make_property()
        response = self.client.get(reverse('property_detail', args=[listing.slug]))
        self.assertContains(response, 'id="enquiry-consent" name="consent_to_contact" required')
        self.assertNotContains(response, 'name="consent_to_contact" value="on"')

    def test_overlong_message_is_rejected(self):
        response = self.client.post(reverse('contact'), dict(ENQUIRY, message='x' * 3001))
        self.assertIn('message', response.context['form'].errors)

    def test_notification_includes_phone_and_listing_and_is_recorded(self):
        listing = make_property(title='Land at Aburi')
        self.client.post(f"{reverse('contact')}?property={listing.slug}", ENQUIRY)
        enquiry = ContactMessage.objects.get()
        self.assertIsNotNone(enquiry.notification_sent_at)
        self.assertEqual(enquiry.notification_error, '')
        body = mail.outbox[0].body
        self.assertIn('+233 24 000 0000', body)
        self.assertIn(listing.reference_number, body)
        self.assertIn(f'/property/{listing.slug}/', body)
        self.assertIn(f'/admin/core/contactmessage/{enquiry.pk}/change/', body)
        self.assertIn('Land at Aburi', mail.outbox[0].subject)

    def test_newlines_in_name_cannot_inject_email_headers(self):
        self.client.post(reverse('contact'), dict(ENQUIRY, name='Ama\nBcc: victim@example.com'))
        self.assertNotIn('\n', mail.outbox[0].subject)

    @override_settings(EMAIL_BACKEND='core.tests.FailingEmailBackend')
    def test_email_failure_keeps_enquiry_and_reassures_visitor(self):
        with self.assertLogs('core.views', level='ERROR'):
            response = self.client.post(reverse('contact'), ENQUIRY, follow=True)
        enquiry = ContactMessage.objects.get()
        self.assertIn('SMTPException', enquiry.notification_error)
        self.assertIsNone(enquiry.notification_sent_at)
        self.assertContains(response, 'Thank you for contacting EmanHomes')
        self.assertNotContains(response, 'delayed')


@override_settings(SECURE_SSL_REDIRECT=False)
class SiteConfigurationTests(TestCase):
    def test_footer_uses_configured_hours_and_socials(self):
        SiteConfiguration.objects.create(
            business_hours='Open 24 hours, every day', tiktok='https://www.tiktok.com/@emanhomesltd',
        )
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Open 24 hours, every day')
        self.assertContains(response, 'href="https://www.tiktok.com/@emanhomesltd"')
        self.assertContains(response, 'aria-label="EmanHomes on TikTok"')

    def test_whatsapp_number_is_digits_only(self):
        config = SiteConfiguration(whatsapp_phone='+233 20 584 3775')
        self.assertEqual(config.whatsapp_number, '233205843775')

    def test_social_link_migration_fills_only_empty_fields(self):
        migration = importlib.import_module('core.migrations.0013_fill_official_social_links')
        empty = SiteConfiguration.objects.create(twitter=None, linkedin='https://linkedin.com/custom')
        migration.fill_empty_social_links(django_apps, None)
        empty.refresh_from_db()
        self.assertEqual(empty.twitter, 'https://x.com/eman_homes')
        self.assertEqual(empty.linkedin, 'https://linkedin.com/custom')


@override_settings(SECURE_SSL_REDIRECT=False)
class StaffRolesAndAdminTests(TestCase):
    def test_roles_exist_with_least_privilege(self):
        def perms(name):
            return set(Group.objects.get(name=name).permissions.values_list('codename', flat=True))

        self.assertIn('change_property', perms('Property managers'))
        self.assertEqual(perms('Enquiry managers'), {'change_contactmessage', 'view_contactmessage', 'view_property'})
        self.assertNotIn('delete_contactmessage', perms('Property managers'))
        self.assertTrue({'add_siteconfiguration', 'change_siteconfiguration'} <= perms('Content editors'))

    def test_admin_requires_login(self):
        response = self.client.get('/admin/core/contactmessage/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_enquiry_manager_cannot_edit_listings(self):
        user = User.objects.create_user('enquiries', password='pw-12345!x', is_staff=True)
        user.groups.add(Group.objects.get(name='Enquiry managers'))
        self.client.force_login(user)
        listing = make_property()
        self.assertEqual(self.client.get('/admin/core/contactmessage/').status_code, 200)
        self.assertEqual(self.client.get(f'/admin/core/property/{listing.pk}/change/').status_code, 200)
        response = self.client.post(f'/admin/core/property/{listing.pk}/change/', {'title': 'Changed'})
        self.assertEqual(response.status_code, 403)

    def test_admin_actions_publish_and_mark_sold(self):
        admin_user = User.objects.create_superuser('boss', 'boss@example.com', 'pw-12345!x')
        self.client.force_login(admin_user)
        draft = make_property(publication_status=Property.DRAFT)
        for action in ('publish', 'mark_sold'):
            self.client.post('/admin/core/property/', {'action': action, '_selected_action': [draft.pk]})
        draft.refresh_from_db()
        self.assertEqual(draft.publication_status, Property.PUBLISHED)
        self.assertEqual(draft.status, 'sold')

    def test_enquiries_cannot_be_created_in_admin(self):
        admin_user = User.objects.create_superuser('boss', 'boss@example.com', 'pw-12345!x')
        self.client.force_login(admin_user)
        self.assertEqual(self.client.get('/admin/core/contactmessage/add/').status_code, 403)


class ZeroDowntimeMigrationTests(TestCase):
    """Code from the previous release keeps running while a deploy's migrations apply."""

    def test_previous_release_can_still_insert_enquiries_and_listings(self):
        from django.db import connection

        with connection.cursor() as cursor:
            # Exactly the columns the previous release knew about.
            cursor.execute(
                "INSERT INTO core_contactmessage (name, email, subject, message, inquiry_type, preferred_contact,"
                " source, consent_to_contact, lead_status, internal_notes, created_at)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                ['Old worker', 'old@example.com', 'Hi', 'Saved mid-deploy', 'general', 'email',
                 'website', True, 'new', '', timezone.now()],
            )
            cursor.execute(
                "INSERT INTO core_property (title, slug, reference_number, category, status, is_featured, currency,"
                " price, location, description, property_size_unit, amenities, bedrooms, bathrooms, main_image,"
                " video_url, created_at)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                ['Old listing', 'old-listing', 'EH-OLD', 'land', 'for_sale', False, 'GHS', 1000, 'Aburi', 'Plot',
                 'plots', '', 0, 0, '', '', timezone.now()],
            )
        enquiry = ContactMessage.objects.get(name='Old worker')
        self.assertEqual((enquiry.phone, enquiry.notification_error), ('', ''))
        listing = Property.objects.get(slug='old-listing')
        self.assertEqual(listing.publication_status, Property.PUBLISHED)
        self.assertIsNotNone(listing.updated_at)

    def test_backfill_uses_creation_time_for_existing_listings(self):
        migration = importlib.import_module('core.migrations.0014_db_defaults_and_updated_at_backfill')
        listing = make_property()
        Property.objects.filter(pk=listing.pk).update(created_at=timezone.now() - timedelta(days=200))
        migration.backfill_updated_at(django_apps, None)
        listing.refresh_from_db()
        self.assertEqual(listing.updated_at, listing.created_at)


class MediaStorageDiagnosticsTests(TestCase):
    def run_command(self):
        from io import StringIO

        from django.core.management import call_command
        out = StringIO()
        call_command('check_media_storage', stdout=out)
        return out.getvalue()

    @override_settings(USE_CLOUDINARY_MEDIA=False)
    def test_reports_filesystem_when_cloudinary_not_configured(self):
        self.assertIn('local filesystem', self.run_command())

    @override_settings(USE_CLOUDINARY_MEDIA=True)
    def test_reports_valid_cloudinary_credentials(self):
        from unittest import mock
        with mock.patch('cloudinary.api.ping', return_value={'status': 'ok'}):
            self.assertIn('Cloudinary credentials OK', self.run_command())

    @override_settings(USE_CLOUDINARY_MEDIA=True)
    def test_explains_rejected_cloudinary_credentials(self):
        from unittest import mock

        import cloudinary.exceptions
        from django.core.management.base import CommandError
        with mock.patch('cloudinary.api.ping', side_effect=cloudinary.exceptions.Error('Invalid api_key 123')):
            with self.assertRaisesMessage(CommandError, 'Invalid api_key 123'):
                self.run_command()


@override_settings(SECURE_SSL_REDIRECT=False)
class AdminUploadFailureTests(TestCase):
    def test_rejected_upload_shows_clear_message_instead_of_error_page(self):
        from unittest import mock

        import cloudinary.exceptions
        from django.contrib import admin as django_admin
        admin_user = User.objects.create_superuser('boss', 'boss@example.com', 'pw-12345!x')
        self.client.force_login(admin_user)
        with mock.patch.object(
            django_admin.ModelAdmin, 'changeform_view',
            side_effect=cloudinary.exceptions.Error('Invalid api_key 123'),
        ), self.assertLogs('core.admin', level='ERROR'):
            response = self.client.post('/admin/core/property/add/', {'title': 'Plot'})
        self.assertRedirects(response, '/admin/core/property/add/', fetch_redirect_response=False)
        page = self.client.get('/admin/core/property/add/')
        self.assertContains(page, 'image storage service rejected the upload')
        self.assertFalse(Property.objects.exists())


# --- Phase 4: enquiry protection ------------------------------------------------------

def signed_form_token(seconds_ago):
    from django.core import signing

    from .spam import FORM_TOKEN_SALT
    return signing.dumps(time.time() - seconds_ago, salt=FORM_TOKEN_SALT)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SECURE_SSL_REDIRECT=False,
    ENQUIRY_RATE_LIMIT=(1000, 600),
)
class SpamProtectionTests(TestCase):
    def test_filled_honeypot_looks_successful_but_saves_nothing(self):
        with self.assertLogs('core.views', level='INFO'):
            response = self.client.post(reverse('contact'), dict(ENQUIRY, website='https://spam.example'))
        self.assertRedirects(response, reverse('enquiry_thanks'))
        self.assertFalse(ContactMessage.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_instant_submission_is_discarded(self):
        with self.assertLogs('core.views', level='INFO'):
            response = self.client.post(reverse('contact'), dict(ENQUIRY, form_started=signed_form_token(0)))
        self.assertRedirects(response, reverse('enquiry_thanks'))
        self.assertFalse(ContactMessage.objects.exists())

    def test_human_paced_submission_is_saved(self):
        response = self.client.post(reverse('contact'), dict(ENQUIRY, form_started=signed_form_token(20)))
        self.assertRedirects(response, reverse('enquiry_thanks'))
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_missing_or_forged_token_is_not_treated_as_spam(self):
        # Pages cached before this release have no token; forged tokens fail the signature.
        self.client.post(reverse('contact'), ENQUIRY)
        self.client.post(reverse('contact'), dict(ENQUIRY, form_started='forged-token'))
        self.assertEqual(ContactMessage.objects.count(), 2)

    def test_forms_render_honeypot_and_token(self):
        contact_page = self.client.get(reverse('contact'))
        self.assertContains(contact_page, 'class="hp-field" aria-hidden="true"')
        self.assertContains(contact_page, 'name="form_started"')
        listing = make_property()
        detail = self.client.get(reverse('property_detail', args=[listing.slug]))
        self.assertContains(detail, 'name="website" autocomplete="off" tabindex="-1"')
        self.assertRegex(detail.content.decode(), r'name="form_started" value="[^"]+"')

    def test_thank_you_page_is_not_indexed(self):
        response = self.client.get(reverse('enquiry_thanks'))
        self.assertContains(response, 'Thank you for contacting EmanHomes')
        self.assertContains(response, '<meta name="robots" content="noindex">')


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SECURE_SSL_REDIRECT=False,
    ENQUIRY_RATE_LIMIT=(3, 600),
)
class EnquiryRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_limit_blocks_excess_submissions_from_one_ip(self):
        for _ in range(3):
            self.assertEqual(self.client.post(reverse('contact'), ENQUIRY).status_code, 302)
        with self.assertLogs('core.views', level='WARNING'):
            response = self.client.post(reverse('contact'), ENQUIRY)
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'Please wait a few minutes', status_code=429)
        self.assertEqual(ContactMessage.objects.count(), 3)

    def test_limit_is_per_visitor_ip(self):
        for _ in range(3):
            self.client.post(reverse('contact'), ENQUIRY, HTTP_CF_CONNECTING_IP='198.51.100.1')
        response = self.client.post(reverse('contact'), ENQUIRY, HTTP_CF_CONNECTING_IP='198.51.100.2')
        self.assertEqual(response.status_code, 302)

    def test_client_ip_prefers_cloudflare_header(self):
        from django.test import RequestFactory

        from .spam import client_ip
        factory = RequestFactory()
        self.assertEqual(client_ip(factory.get('/', HTTP_CF_CONNECTING_IP='203.0.113.9',
                                               HTTP_X_FORWARDED_FOR='10.0.0.1')), '203.0.113.9')
        self.assertEqual(client_ip(factory.get('/', HTTP_X_FORWARDED_FOR='203.0.113.7, 10.0.0.1')), '203.0.113.7')
        self.assertEqual(client_ip(factory.get('/')), '127.0.0.1')


# --- Legal pages and official Facebook ----------------------------------------------

@override_settings(SECURE_SSL_REDIRECT=False)
class LegalPageTests(TestCase):
    def publish(self, slug):
        LegalPage.objects.filter(slug=slug).update(status=LegalPage.PUBLISHED)

    def test_drafts_are_seeded_and_hidden_from_public(self):
        self.assertEqual(set(LegalPage.objects.values_list('slug', 'status')),
                         {('privacy', 'draft'), ('terms', 'draft')})
        for url in ('/privacy/', '/terms/'):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_drafts_are_not_linked_or_listed(self):
        self.assertNotContains(self.client.get(reverse('contact')), 'privacy policy</a>')
        self.assertNotContains(self.client.get(reverse('home')), 'href="/terms/"')
        self.assertNotContains(self.client.get('/sitemap.xml'), '/privacy/')

    def test_staff_can_review_draft_with_warning(self):
        staff = User.objects.create_user('editor', password='pw-12345!x', is_staff=True)
        self.client.force_login(staff)
        response = self.client.get('/privacy/')
        self.assertContains(response, 'DRAFT – not legally approved')
        self.assertContains(response, 'Data Protection Act, 2012 (Act 843)')
        self.assertContains(response, '<meta name="robots" content="noindex">')

    def test_published_pages_are_public_and_linked(self):
        self.publish('privacy')
        self.publish('terms')
        page = self.client.get('/privacy/')
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'DRAFT')
        self.assertContains(self.client.get(reverse('contact')), 'See our <a href="/privacy/"')
        listing = make_property()
        self.assertContains(self.client.get(reverse('property_detail', args=[listing.slug])), 'href="/privacy/"')
        home = self.client.get(reverse('home'))
        self.assertContains(home, 'href="/terms/"')
        sitemap = self.client.get('/sitemap.xml')
        self.assertContains(sitemap, '/privacy/')
        self.assertContains(sitemap, '/terms/')

    def test_admin_can_edit_but_not_add_or_delete(self):
        boss = User.objects.create_superuser('boss', 'boss@example.com', 'pw-12345!x')
        self.client.force_login(boss)
        privacy = LegalPage.objects.get(slug='privacy')
        self.assertEqual(self.client.get(f'/admin/core/legalpage/{privacy.pk}/change/').status_code, 200)
        self.assertEqual(self.client.get('/admin/core/legalpage/add/').status_code, 403)
        self.assertEqual(self.client.get(f'/admin/core/legalpage/{privacy.pk}/delete/').status_code, 403)

    def test_staff_with_edit_permission_still_cannot_publish(self):
        from django.contrib.auth.models import Permission
        editor = User.objects.create_user('legal-editor', password='pw-12345!x', is_staff=True)
        editor.user_permissions.add(*Permission.objects.filter(codename__in=['change_legalpage', 'view_legalpage']))
        self.client.force_login(editor)
        privacy = LegalPage.objects.get(slug='privacy')
        self.client.post(f'/admin/core/legalpage/{privacy.pk}/change/', {
            'title': 'Privacy policy', 'body': 'Edited draft', 'status': 'published', 'approval_note': 'self-approved',
        })
        privacy.refresh_from_db()
        self.assertEqual(privacy.body, 'Edited draft')
        self.assertEqual(privacy.status, LegalPage.DRAFT)
        self.assertEqual(privacy.approval_note, '')

    def test_content_roles_cannot_publish_legal_pages(self):
        for group in Group.objects.all():
            self.assertFalse(group.permissions.filter(codename='change_legalpage').exists(), group.name)


class SimpleFormatTests(TestCase):
    def render(self, text):
        from .templatetags.content import simple_format
        return str(simple_format(text))

    def test_structure(self):
        html = self.render('Intro line\n\n## Heading\n- one\n- two\n\nPara one\nline two')
        self.assertIn('<p>Intro line</p>', html)
        self.assertIn('<h2>Heading</h2>', html)
        self.assertIn('<ul><li>one</li><li>two</li></ul>', html)
        self.assertIn('<p>Para one<br>line two</p>', html)

    def test_html_is_escaped(self):
        html = self.render('## <img src=x onerror=alert(1)>\n<script>alert(1)</script>\n\n- <b>x</b>')
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img', html)
        self.assertNotIn('<b>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_emails_become_links(self):
        self.assertIn('href="mailto:emanpages@gmail.com"', self.render('Email: emanpages@gmail.com'))


class OfficialFacebookTests(TestCase):
    def test_migration_replaces_old_default_but_keeps_custom_value(self):
        migration = importlib.import_module('core.migrations.0016_seed_legal_drafts_and_official_facebook')
        old = SiteConfiguration.objects.create(facebook='https://www.facebook.com/emanhomes')
        custom = SiteConfiguration.objects.create(facebook='https://www.facebook.com/someotherpage')
        migration.seed(django_apps, None)
        old.refresh_from_db()
        custom.refresh_from_db()
        self.assertEqual(old.facebook, 'https://www.facebook.com/emanhomesofficial')
        self.assertEqual(custom.facebook, 'https://www.facebook.com/someotherpage')

    def test_new_configuration_uses_official_page(self):
        self.assertEqual(SiteConfiguration().facebook, 'https://www.facebook.com/emanhomesofficial')


# --- Phase 5: services, landing pages, content and accessibility ----------------------

@override_settings(SECURE_SSL_REDIRECT=False)
class ServicesPageTests(TestCase):
    def test_spec_services_are_seeded_in_order(self):
        titles = list(Service.objects.values_list('title', flat=True))
        self.assertEqual(titles, ['Land sales', 'House sales', 'Property development',
                                  'Rentals and leasing', 'Construction', 'Property refurbishment'])

    def test_seed_does_not_touch_existing_services(self):
        migration = importlib.import_module('core.migrations.0018_seed_services_if_empty')
        before = Service.objects.count()
        migration.seed_services(django_apps, None)
        self.assertEqual(Service.objects.count(), before)

    def test_page_lists_active_services_only(self):
        Service.objects.filter(title='Construction').update(is_active=False)
        response = self.client.get(reverse('services'))
        self.assertContains(response, 'Land sales')
        self.assertNotContains(response, 'Construction services for homes')

    def test_enquire_button_prefills_contact_form(self):
        service = Service.objects.get(title='Property refurbishment')
        response = self.client.get(reverse('contact'), {'service': service.pk})
        self.assertEqual(response.context['form'].initial['subject'], 'Enquiry about property refurbishment')

    def test_unknown_or_inactive_service_is_ignored(self):
        service = Service.objects.get(title='Construction')
        service.is_active = False
        service.save()
        for value in (service.pk, 99999, 'abc'):
            response = self.client.get(reverse('contact'), {'service': value})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('subject', response.context['form'].initial)


@override_settings(SECURE_SSL_REDIRECT=False)
class LandingPageTests(TestCase):
    def setUp(self):
        make_property(title='Plot at Aburi', category='land')
        make_property(title='Family house', category='residential')
        make_property(title='Office space', category='commercial')
        make_property(title='Apartment to rent', category='residential', status='for_rent')

    def titles(self, response):
        return {p.title for p in response.context['properties']}

    def test_land_page(self):
        response = self.client.get(reverse('properties_land'))
        self.assertEqual(self.titles(response), {'Plot at Aburi'})
        self.assertContains(response, '<title>Land and plots in Ghana | EmanHomes</title>', html=False)

    def test_houses_page(self):
        response = self.client.get(reverse('properties_houses'))
        self.assertEqual(self.titles(response), {'Family house', 'Apartment to rent'})

    def test_rentals_page(self):
        response = self.client.get(reverse('properties_rentals'))
        self.assertEqual(self.titles(response), {'Apartment to rent'})

    def test_landing_filter_cannot_be_overridden_by_query(self):
        response = self.client.get(reverse('properties_land'), {'category': 'commercial'})
        self.assertEqual(self.titles(response), {'Plot at Aburi'})

    def test_landing_page_keeps_other_filters(self):
        response = self.client.get(reverse('properties_houses'), {'status': 'for_rent'})
        self.assertEqual(self.titles(response), {'Apartment to rent'})

    def test_rentals_link_and_sitemap_entry_only_when_rentals_exist(self):
        home = self.client.get(reverse('home'))
        self.assertContains(home, 'href="/properties/rentals/"')
        self.assertContains(self.client.get('/sitemap.xml'), '/properties/rentals/')
        Property.objects.filter(status='for_rent').update(status='rented')
        home = self.client.get(reverse('home'))
        self.assertNotContains(home, 'href="/properties/rentals/"')
        self.assertNotContains(self.client.get('/sitemap.xml'), '/properties/rentals/')

    def test_sitemap_lists_new_pages(self):
        sitemap = self.client.get('/sitemap.xml')
        for path in ('/services/', '/properties/land/', '/properties/houses/'):
            self.assertContains(sitemap, path)


@override_settings(SECURE_SSL_REDIRECT=False)
class ContentAndAccessibilityTests(TestCase):
    PAGES = ('home', 'about', 'services', 'properties_list', 'contact')

    def test_no_stock_photos_or_unconfirmed_claims(self):
        for name in self.PAGES:
            html = self.client.get(reverse(name)).content.decode()
            for banned in ('unsplash.com', 'Premium', 'Meet the Experts', 'cleaning services',
                           'Delivering Excellence'):
                self.assertNotIn(banned, html, f'{banned!r} on {name}')

    def test_pages_have_skip_link_and_main_landmark(self):
        for name in self.PAGES:
            response = self.client.get(reverse(name))
            self.assertContains(response, 'href="#main">Skip to main content</a>')
            self.assertContains(response, '<main id="main" tabindex="-1">')

    def test_titles_are_unique(self):
        titles = set()
        for name in self.PAGES:
            title = re.search(r'<title>(.*?)</title>', self.client.get(reverse(name)).content.decode(), re.S).group(1)
            self.assertNotIn(title, titles)
            titles.add(title)

    def test_content_visible_without_javascript(self):
        css = (Path(settings.BASE_DIR) / 'static/css/eman-interactions.css').read_text(encoding='utf-8')
        self.assertIn('.js .reveal-on-scroll { opacity: 0;', css)
        self.assertNotRegex(css, r'(?m)^\.reveal-on-scroll \{ opacity: 0')
        self.assertContains(self.client.get(reverse('home')), "document.documentElement.classList.add('js')")

    def test_listing_filters_have_labels(self):
        response = self.client.get(reverse('properties_list'))
        for field in ('filter-category', 'filter-q', 'filter-status', 'filter-bedrooms'):
            self.assertContains(response, f'<label class="visually-hidden" for="{field}">')

    def test_category_tile_uses_real_listing_photo_when_available(self):
        make_property(title='Land with photo', category='land', main_image='properties/aburi.jpg')
        response = self.client.get(reverse('home'))
        self.assertContains(response, "url('/media/properties/aburi.jpg')")

    def test_property_page_enquiry_heading(self):
        listing = make_property()
        self.assertContains(self.client.get(reverse('property_detail', args=[listing.slug])),
                            'Enquire about this property')

    def test_about_hides_team_section_without_members(self):
        self.assertNotContains(self.client.get(reverse('about')), 'The people you will work with')


@override_settings(SECURE_SSL_REDIRECT=False)
class LinktreeBadgeTests(TestCase):
    def test_badge_links_to_default_linktree_with_circular_text(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, '<a class="hero-orbit" href="https://linktr.ee/emanhomes" target="_blank" rel="noopener"')
        self.assertContains(response, '<textPath href="#hero-orbit-path"')
        self.assertContains(response, 'VISIT OUR LINKTREE')
        self.assertContains(response, 'aria-label="Visit our Linktree (opens in a new tab)"')

    def test_badge_uses_configured_linktree(self):
        SiteConfiguration.objects.create(linktree='https://linktr.ee/emanhomes-new')
        self.assertContains(self.client.get(reverse('home')), 'href="https://linktr.ee/emanhomes-new"')

    def test_badge_spins_pauses_on_hover_and_respects_reduced_motion(self):
        css = (Path(settings.BASE_DIR) / 'static/css/eman-interactions.css').read_text(encoding='utf-8')
        self.assertIn('.hero-orbit__ring { position: absolute; inset: 0; width: 100%; height: 100%; animation: orbit', css)
        self.assertIn('font-weight: 900', css)
        self.assertIn('.hero-orbit:hover .hero-orbit__ring, .hero-orbit:focus-visible .hero-orbit__ring '
                      '{ animation-play-state: paused; }', css)
        self.assertIn('@media (prefers-reduced-motion: reduce)', css)


@override_settings(SECURE_SSL_REDIRECT=False)
class HeroCarouselTests(TestCase):
    def test_slides_are_current_listings_with_photos(self):
        with_photo = make_property(title='House with photo', main_image='properties/house.jpg')
        make_property(title='Video only')
        make_property(title='Sold with photo', status='sold', main_image='properties/sold.jpg')
        make_property(title='Draft with photo', publication_status=Property.DRAFT, main_image='properties/d.jpg')
        response = self.client.get(reverse('home'))
        slides = response.context['hero_slides']
        self.assertEqual([slide['property'].pk for slide in slides], [with_photo.pk])
        self.assertContains(response, "background-image:url('/media/properties/house.jpg')")
        self.assertContains(response, f'href="/property/{with_photo.slug}/" data-hero-caption')

    def test_gallery_photo_is_used_when_there_is_no_main_image(self):
        from .models import PropertyImage
        listing = make_property(title='Gallery only')
        PropertyImage.objects.create(property=listing, image='properties/gallery/g1.jpg')
        self.assertEqual(self.client.get(reverse('home')).context['hero_slides'][0]['image_url'],
                         '/media/properties/gallery/g1.jpg')

    def test_slides_change_every_45_seconds_without_navy_tint(self):
        self.assertContains(self.client.get(reverse('home')), 'data-interval="45000"')
        css = (Path(settings.BASE_DIR) / 'static/css/eman-interactions.css').read_text(encoding='utf-8')
        overlay = next(line for line in css.splitlines() if line.startswith('.edge-hero__slide::after'))
        self.assertNotIn('7,29,56', overlay)  # the navy tint

    def test_no_photos_falls_back_to_brand_background(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['hero_slides'], [])
        self.assertContains(response, 'edge-hero--no-photos')
        self.assertNotContains(response, 'data-hero-caption')

    def test_headline_is_editable_and_has_no_unprovable_claim(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Your trusted partner for land and property in Ghana')
        self.assertNotContains(response, 'No.1')
        SiteConfiguration.objects.create(hero_headline='Homes and land across Ghana')
        self.assertContains(self.client.get(reverse('home')), 'Homes and land across Ghana')


@override_settings(SECURE_SSL_REDIRECT=False)
class HeroCarouselReviewTests(TestCase):
    def test_empty_gallery_rows_do_not_take_slots(self):
        from .models import PropertyImage
        real = make_property(title='Older listing with real photo', main_image='properties/real.jpg')
        Property.objects.filter(pk=real.pk).update(created_at=timezone.now() - timedelta(days=30))
        for n in range(8):
            empty = make_property(title=f'Empty gallery row {n}')
            PropertyImage.objects.create(property=empty, image='')
        slides = self.client.get(reverse('home')).context['hero_slides']
        self.assertEqual([slide['property'].pk for slide in slides], [real.pk])

    def test_one_gallery_query_regardless_of_gallery_size(self):
        from .models import PropertyImage
        from .views import hero_slides
        for n in range(8):
            listing = make_property(title=f'Gallery listing {n}')
            for photo in range(6):
                PropertyImage.objects.create(property=listing, image=f'properties/gallery/{n}-{photo}.jpg',
                                             display_order=photo)
        with self.assertNumQueries(2):
            slides = hero_slides()
        self.assertEqual(len(slides), 8)
        self.assertTrue(all(slide['image_url'].endswith('-0.jpg') for slide in slides))

    def test_ties_are_ordered_consistently(self):
        stamp = timezone.now()
        listings = [make_property(title=f'Tied {n}', main_image=f'properties/t{n}.jpg') for n in range(10)]
        Property.objects.filter(pk__in=[p.pk for p in listings]).update(created_at=stamp)
        from .views import hero_slides
        self.assertEqual([s['property'].pk for s in hero_slides()], sorted(p.pk for p in listings)[:8])


@override_settings(SECURE_SSL_REDIRECT=False)
class GalleryOnlyListingAdminTests(TestCase):
    def setUp(self):
        import tempfile
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.client.force_login(User.objects.create_superuser('boss', 'boss@example.com', 'pw-12345!x'))

    def tearDown(self):
        import shutil
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def post_listing(self, gallery_image=None):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        data = {
            'title': 'Gallery only plot', 'slug': '', 'category': 'land', 'status': 'for_sale',
            'publication_status': 'published', 'currency': 'GHS', 'price': '1000', 'location': 'Aburi',
            'description': 'Plot', 'bedrooms': '0', 'bathrooms': '0', 'property_size_unit': 'plots',
            'amenities': '', 'video_url': '', 'seo_title': '', 'seo_description': '',
            'gallery-TOTAL_FORMS': '1', 'gallery-INITIAL_FORMS': '0',
            'gallery-MIN_NUM_FORMS': '0', 'gallery-MAX_NUM_FORMS': '1000',
            'gallery-0-alt_text': 'Plot view', 'gallery-0-caption': '', 'gallery-0-display_order': '0',
        }
        if gallery_image:
            buffer = BytesIO()
            Image.new('RGB', (40, 30), (120, 160, 90)).save(buffer, 'JPEG')
            data['gallery-0-image'] = SimpleUploadedFile('plot.jpg', buffer.getvalue(), content_type='image/jpeg')
        return self.client.post('/admin/core/property/add/', data)

    def test_listing_with_only_a_gallery_photo_can_be_saved(self):
        response = self.post_listing(gallery_image=True)
        self.assertEqual(response.status_code, 302, getattr(response, 'context', None) and
                         response.context['inline_admin_formsets'][0].formset.non_form_errors())
        listing = Property.objects.get(title='Gallery only plot')
        self.assertEqual(listing.gallery.count(), 1)

    def test_listing_with_no_photo_or_video_is_rejected(self):
        response = self.post_listing(gallery_image=False)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add a main image, a gallery photo or a video link.')
        self.assertFalse(Property.objects.filter(title='Gallery only plot').exists())


@override_settings(SECURE_SSL_REDIRECT=False)
class ListingPhotoTests(TestCase):
    def test_gallery_rows_without_files_never_crash_pages(self):
        from .models import PropertyImage
        listing = make_property(title='Has an empty gallery row')
        PropertyImage.objects.create(property=listing, image='')
        for url in (reverse('home'), reverse('properties_list'), reverse('property_detail', args=[listing.slug])):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_gallery_only_listing_shows_its_photos(self):
        from .models import PropertyImage
        listing = make_property(title='Gallery only', video_url='')
        PropertyImage.objects.create(property=listing, image='properties/gallery/a.jpg', display_order=1)
        PropertyImage.objects.create(property=listing, image='properties/gallery/b.jpg', display_order=2)
        self.assertEqual(listing.cover_image_url, '/media/properties/gallery/a.jpg')
        detail = self.client.get(reverse('property_detail', args=[listing.slug]))
        self.assertNotContains(detail, 'No Image Available')
        self.assertContains(detail, '/media/properties/gallery/b.jpg')
        self.assertContains(self.client.get(reverse('properties_list')), 'src="/media/properties/gallery/a.jpg"')


@override_settings(SECURE_SSL_REDIRECT=False)
class ListingSortTests(TestCase):
    def setUp(self):
        self.cheap_ghs = make_property(title='Cheap GHS', currency='GHS', price=Decimal('50000'))
        self.dear_ghs = make_property(title='Dear GHS', currency='GHS', price=Decimal('900000'))
        self.cheap_usd = make_property(title='Cheap USD', currency='USD', price=Decimal('20000'))
        self.dear_usd = make_property(title='Dear USD', currency='USD', price=Decimal('300000'), is_featured=True)
        self.on_request = make_property(title='On request', currency='GHS', price=None)
        self.sold = make_property(title='Sold cheap', currency='GHS', price=Decimal('1'), status='sold')

    def titles(self, sort):
        response = self.client.get(reverse('properties_list'), {'sort': sort})
        return [p.title for p in response.context['properties']]

    def test_price_low_to_high_groups_currencies_and_puts_unpriced_and_sold_last(self):
        self.assertEqual(self.titles('price_asc'),
                         ['Cheap GHS', 'Dear GHS', 'On request', 'Cheap USD', 'Dear USD', 'Sold cheap'])

    def test_price_high_to_low(self):
        self.assertEqual(self.titles('price_desc'),
                         ['Dear GHS', 'Cheap GHS', 'On request', 'Dear USD', 'Cheap USD', 'Sold cheap'])

    def test_newest_ignores_featured(self):
        self.assertEqual(self.titles('newest')[0], 'On request')
        self.assertEqual(self.titles('newest')[-1], 'Sold cheap')

    def test_recommended_and_unknown_sort_keep_featured_first(self):
        for sort in ('', 'bogus'):
            self.assertEqual(self.titles(sort)[0], 'Dear USD', sort)

    def test_sort_control_keeps_filters_and_explains_currencies(self):
        response = self.client.get(reverse('properties_list'), {'category': 'residential', 'sort': 'price_asc'})
        self.assertContains(response, '<input type="hidden" name="category" value="residential">')
        self.assertContains(response, '<option value="price_asc" selected>')
        self.assertContains(response, 'are sorted separately')
        self.assertContains(response, 'role="status">6 listings</p>')

    def test_sort_works_on_landing_pages(self):
        response = self.client.get(reverse('properties_houses'), {'sort': 'price_desc'})
        self.assertEqual([p.title for p in response.context['properties']][0], 'Dear GHS')


class BrandColourTests(TestCase):
    @staticmethod
    def contrast(hex_a, hex_b):
        def luminance(hex_colour):
            channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
        lighter, darker = sorted((luminance(hex_a), luminance(hex_b)), reverse=True)
        return (lighter + 0.05) / (darker + 0.05)

    def read(self, relative):
        return (Path(settings.BASE_DIR) / relative).read_text(encoding='utf-8')

    def test_tokens_match_the_logo(self):
        base = self.read('templates/core/base.html')
        self.assertIn('--primary: #00183A;', base)
        self.assertIn('--accent: #E40021;', base)

    def test_old_palette_is_gone(self):
        for relative in ('templates/core/base.html', 'templates/core/home.html', 'templates/500.html',
                         'static/css/eman-interactions.css'):
            text = self.read(relative).lower()
            for old in ('#0d2e59', '#071d38', '#d72638', '#a51c30', 'rgba(13,46,89', 'rgba(7,29,56', 'rgba(215,38,56'):
                self.assertNotIn(old, text, f'{old} in {relative}')

    def test_text_on_brand_colours_meets_wcag_aa(self):
        self.assertGreaterEqual(self.contrast('#FFFFFF', '#E40021'), 4.5)  # white on buttons
        self.assertGreaterEqual(self.contrast('#FFFFFF', '#B5001A'), 4.5)  # white on hover
        self.assertGreaterEqual(self.contrast('#FFFFFF', '#00183A'), 4.5)  # white on navy
        self.assertGreaterEqual(self.contrast('#E40021', '#FFFFFF'), 4.5)  # red text on white

    def test_no_navy_text_on_red(self):
        css = self.read('templates/core/base.html') + self.read('static/css/eman-interactions.css')
        for line in css.splitlines():
            if 'background: var(--accent)' in line or 'background-color: var(--accent)' in line:
                self.assertNotIn('color: var(--primary)', line, line)

    def test_floating_buttons_clear_the_mobile_action_bar(self):
        css = self.read('static/css/eman-interactions.css')
        self.assertIn('body:has(.mobile-action-bar) .fab-container { bottom: 5.25rem;', css)
        self.assertIn('body:has(.mobile-action-bar) .fab-phone { display: none; }', css)


class BannerHeadingTests(TestCase):
    def test_headings_inside_navy_banners_are_white(self):
        base = (Path(settings.BASE_DIR) / 'templates/core/base.html').read_text(encoding='utf-8')
        self.assertIn('.bg-primary-custom :is(h1, h2, h3, h4, h5, h6) { color: #fff; }', base)


@override_settings(SECURE_SSL_REDIRECT=False, SITE_URL='https://emanhomes.com', SITE_NOINDEX=False)
class SeoAndSharingTests(TestCase):
    def head(self, url, **extra):
        html = self.client.get(url, **extra).content.decode()
        return html.split('</head>')[0]

    def jsonld(self, html):
        import json
        return [json.loads(block) for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]

    def test_share_tags_reuse_page_title_and_description(self):
        head = self.head(reverse('services'))
        self.assertIn('<title>Real estate services | EmanHomes</title>', head)
        description = re.search(r'<meta name="description" content="([^"]+)"', head).group(1)
        self.assertIn(f'<meta property="og:description" content="{description}">', head)
        self.assertIn('<meta property="og:title" content="Real estate services">', head)
        self.assertIn('<meta name="twitter:card" content="summary_large_image">', head)

    def test_canonical_and_og_url_use_the_main_domain(self):
        head = self.head(reverse('services'), HTTP_HOST='testserver')
        self.assertIn('<link rel="canonical" href="https://emanhomes.com/services/">', head)
        self.assertIn('<meta property="og:url" content="https://emanhomes.com/services/">', head)

    def test_default_share_image_is_absolute_logo(self):
        self.assertIn('<meta property="og:image" content="https://emanhomes.com/static/img/logo.jpeg">',
                      self.head(reverse('home')))

    def test_listing_shares_its_own_photo(self):
        listing = make_property(title='Villa with photo', main_image='properties/villa.jpg')
        head = self.head(reverse('property_detail', args=[listing.slug]))
        self.assertIn('<meta property="og:image" content="https://emanhomes.com/media/properties/villa.jpg">', head)
        self.assertIn('<meta property="og:title" content="Villa with photo in Oyarifa">', head)

    def test_homepage_business_structured_data(self):
        SiteConfiguration.objects.create(tiktok='https://www.tiktok.com/@emanhomesltd')
        data = self.jsonld(self.client.get(reverse('home')).content.decode())[0]
        self.assertEqual(data['@type'], 'RealEstateAgent')
        self.assertEqual(data['name'], 'Eman Homes Limited GH')
        self.assertEqual(data['telephone'], '+233 20 584 3775')
        self.assertEqual(data['address']['streetAddress'], 'Dzen-Ayor, East Legon, Accra, Ghana')
        self.assertEqual(data['openingHoursSpecification']['opens'], '00:00')
        self.assertIn('https://www.facebook.com/emanhomesofficial', data['sameAs'])
        self.assertIn('https://www.tiktok.com/@emanhomesltd', data['sameAs'])

    def test_listing_breadcrumbs(self):
        listing = make_property(title='Plot', category='land')
        data = self.jsonld(self.client.get(reverse('property_detail', args=[listing.slug])).content.decode())[0]
        self.assertEqual([item['name'] for item in data['itemListElement']], ['Home', 'Properties', 'Land', 'Plot'])
        self.assertEqual(data['itemListElement'][-1]['item'], f'https://emanhomes.com/property/{listing.slug}/')

    def test_structured_data_cannot_break_out_of_its_script_tag(self):
        listing = make_property(title='</script><script>alert(1)</script>', category='land')
        html = self.client.get(reverse('property_detail', args=[listing.slug])).content.decode()
        self.assertNotIn('<script>alert(1)', html)
        self.assertEqual(self.jsonld(html)[0]['itemListElement'][-1]['name'], listing.title)

    def test_production_is_indexable(self):
        self.assertNotIn('noindex', self.head(reverse('home')))
        self.assertContains(self.client.get('/robots.txt'), 'Allow: /')

    @override_settings(ALLOWED_HOSTS=['*'])
    def test_render_addresses_are_not_indexed(self):
        host = {'HTTP_HOST': 'eman-homes-staging.onrender.com'}
        self.assertIn('<meta name="robots" content="noindex, nofollow">', self.head(reverse('home'), **host))
        robots = self.client.get('/robots.txt', **host)
        self.assertContains(robots, 'Disallow: /')
        self.assertNotContains(robots, 'Sitemap:')

    @override_settings(SITE_NOINDEX=True)
    def test_noindex_setting(self):
        self.assertIn('noindex, nofollow', self.head(reverse('home')))


@override_settings(
    SECURE_SSL_REDIRECT=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    ADMINS=[('EmanHomes admin', 'alerts@example.com')],
    EMAIL_SUBJECT_PREFIX='[EmanHomes] ',
)
class ErrorAlertTests(TestCase):
    def test_server_error_emails_admins(self):
        from unittest import mock
        self.client.raise_request_exception = False
        # No assertLogs here: it swaps out the logger's handlers, including the email one under test.
        with mock.patch('core.views.Service.objects.filter', side_effect=RuntimeError('database exploded')):
            response = self.client.get(reverse('services'))
        self.assertEqual(response.status_code, 500)
        alerts = [m for m in mail.outbox if m.to == ['alerts@example.com']]
        self.assertEqual(len(alerts), 1)
        self.assertTrue(alerts[0].subject.startswith('[EmanHomes] ERROR'))
        self.assertIn('database exploded', alerts[0].body)

    def test_not_found_pages_do_not_send_alerts(self):
        self.client.get('/definitely-not-here/')
        self.assertEqual(mail.outbox, [])

    def test_admins_default_to_lead_inbox(self):
        import os
        import subprocess
        import sys
        env = {k: v for k, v in os.environ.items() if k not in ('ADMIN_EMAILS', 'RENDER')}
        env.update(SECRET_KEY='test', DJANGO_SETTINGS_MODULE='emanhomes_project.settings',
                   LEAD_NOTIFICATION_EMAIL='leads@example.com')
        result = subprocess.run([sys.executable, '-c', 'import django; django.setup(); from django.conf import '
                                 'settings; print(settings.ADMINS)'], env=env, capture_output=True, text=True)
        self.assertIn("('EmanHomes admin', 'leads@example.com')", result.stdout, result.stderr)


@override_settings(SECURE_SSL_REDIRECT=False)
class SearchConsoleVerificationTests(TestCase):
    @override_settings(GOOGLE_SITE_VERIFICATION='abc123-token')
    def test_tag_rendered_when_configured(self):
        self.assertContains(self.client.get(reverse('home')),
                            '<meta name="google-site-verification" content="abc123-token">')

    @override_settings(GOOGLE_SITE_VERIFICATION='')
    def test_no_tag_by_default(self):
        self.assertNotContains(self.client.get(reverse('home')), 'google-site-verification')

    @override_settings(GOOGLE_SITE_VERIFICATION='"><script>alert(1)</script>')
    def test_value_is_escaped(self):
        self.assertNotContains(self.client.get(reverse('home')), '<script>alert(1)')

    def test_company_code_is_the_default(self):
        from django.conf import settings as live_settings
        self.assertEqual(live_settings.GOOGLE_SITE_VERIFICATION, 'x2CvoQFMjuVELAEGCsRY_89qm8Tx5F1CM_FlhX4e5A4')
