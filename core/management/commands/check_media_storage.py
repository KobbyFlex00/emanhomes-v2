"""Verify that media uploads will work, e.g. after changing CLOUDINARY_URL.

Usage (Render Shell):  python manage.py check_media_storage
"""
import cloudinary
import cloudinary.api
import cloudinary.exceptions
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Check that the configured media storage accepts our credentials.'

    def handle(self, *args, **options):
        if not settings.USE_CLOUDINARY_MEDIA:
            self.stdout.write(f'Media uses the local filesystem at {settings.MEDIA_ROOT} (no CLOUDINARY_URL set).')
            return

        cloud_name = cloudinary.config().cloud_name or '(missing)'
        try:
            cloudinary.api.ping()
        except cloudinary.exceptions.Error as exc:
            raise CommandError(
                f'Cloudinary rejected the credentials for cloud "{cloud_name}": {exc}. '
                'Copy the "API environment variable" from Cloudinary > Settings > API Keys '
                'into CLOUDINARY_URL (value only, no quotes), then redeploy.'
            ) from exc
        self.stdout.write(self.style.SUCCESS(f'Cloudinary credentials OK for cloud "{cloud_name}".'))
