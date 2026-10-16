"""
Django settings for emanhomes_project project.
"""
import os
from pathlib import Path

import cloudinary
import cloudinary.api
import cloudinary.uploader
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ImproperlyConfigured('SECRET_KEY must be set in the environment.')

# SECURITY: defaults to False; only set DEBUG=true for local development.
DEBUG = env_bool('DEBUG', False)
if DEBUG and os.environ.get('RENDER'):
    raise ImproperlyConfigured('DEBUG must not be enabled on Render.')

ALLOWED_HOSTS = [host for host in os.environ.get(
    'ALLOWED_HOSTS', 'localhost,127.0.0.1,emanhomes.com,www.emanhomes.com'
).split(',') if host]
CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.environ.get(
        'CSRF_TRUSTED_ORIGINS', 'https://emanhomes.com,https://www.emanhomes.com'
    ).split(',') if origin
]
# Render provides each service's own hostname (e.g. the staging onrender.com URL).
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

INSTALLED_APPS = [
    'cloudinary_storage',
    'django.contrib.admin',
    'django.contrib.auth',
    'cloudinary',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'emanhomes_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.site_configuration',
            ],
        },
    },
]

WSGI_APPLICATION = 'emanhomes_project.wsgi.application'

database_url = os.environ.get('DATABASE_URL')
if database_url:
    DATABASES = {
        'default': dj_database_url.parse(
            database_url,
            conn_max_age=600,
            ssl_require=env_bool('DATABASE_SSL_REQUIRE', True),
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Not read by Django >= 5.1, but django-cloudinary-storage's collectstatic
# command (used with --upload-unhashed-files in the build) still requires it.
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# --- MEDIA (Cloudinary) ---
# Render's disk is ephemeral, so hosted environments must store uploads in
# Cloudinary. Local development and CI fall back to the filesystem.
cloudinary.config(
    secure=True
)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
USE_CLOUDINARY_MEDIA = bool(os.environ.get('CLOUDINARY_URL'))
if os.environ.get('RENDER') and not USE_CLOUDINARY_MEDIA:
    raise ImproperlyConfigured('CLOUDINARY_URL must be set on Render so media uploads persist.')

STORAGES = {
    'default': {
        'BACKEND': (
            'cloudinary_storage.storage.MediaCloudinaryStorage'
            if USE_CLOUDINARY_MEDIA
            else 'django.core.files.storage.FileSystemStorage'
        ),
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- SECURITY (HTTPS) ---
# Secure by default; local development over plain HTTP opts out via DEBUG.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', not DEBUG)
SECURE_REDIRECT_EXEMPT = [r'^healthz/$']  # platform health checks use plain HTTP
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# --- EMAIL (Gmail) ---
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '10'))
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'emanpages@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
LEAD_NOTIFICATION_EMAIL = os.environ.get('LEAD_NOTIFICATION_EMAIL', EMAIL_HOST_USER)

# --- ERROR ALERTS ---
# Unhandled server errors (HTTP 500) are emailed to ADMINS when DEBUG is off.
ADMINS = [
    ('EmanHomes admin', address.strip())
    for address in os.environ.get('ADMIN_EMAILS', LEAD_NOTIFICATION_EMAIL).split(',') if address.strip()
]
SERVER_EMAIL = EMAIL_HOST_USER  # Gmail only sends as the signed-in account
EMAIL_SUBJECT_PREFIX = os.environ.get('EMAIL_SUBJECT_PREFIX', '[EmanHomes] ')

# --- SEO ---
# Canonical address used for canonical links, share previews and structured data.
SITE_URL = os.environ.get('SITE_URL', 'https://emanhomes.com').rstrip('/')
# Ask search engines not to index this deployment (also automatic on *.onrender.com hosts).
SITE_NOINDEX = env_bool('SITE_NOINDEX', False)
ANALYTICS_MEASUREMENT_ID = os.environ.get('ANALYTICS_MEASUREMENT_ID', '')
# Enquiry submissions allowed per visitor IP: (count, window in seconds).
ENQUIRY_RATE_LIMIT = (
    int(os.environ.get('ENQUIRY_RATE_LIMIT_COUNT', '10')),
    int(os.environ.get('ENQUIRY_RATE_LIMIT_WINDOW', '600')),
)
SECURE_HSTS_SECONDS = 0 if DEBUG else int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# --- LOGGING ---
# Render captures stdout/stderr; keep application logs there.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {'format': '%(asctime)s %(levelname)s %(name)s: %(message)s'},
    },
    'filters': {
        'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'standard'},
        'mail_admins': {
            'class': 'django.utils.log.AdminEmailHandler',
            'level': 'ERROR',
            'filters': ['require_debug_false'],
        },
    },
    'root': {'handlers': ['console'], 'level': os.environ.get('LOG_LEVEL', 'INFO')},
    'loggers': {
        # 404s are WARNING (console only); 500s are ERROR and also emailed.
        'django.request': {'handlers': ['console', 'mail_admins'], 'level': 'WARNING', 'propagate': False},
    },
}
