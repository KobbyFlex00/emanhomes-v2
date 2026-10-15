"""Lightweight protection for the public enquiry forms.

Three layers, none of which bother real visitors:
- a honeypot field that is off-screen for people but filled in by bots,
- a signed "form started" timestamp that flags submissions made faster than a person can type,
- a per-IP rate limit on submissions.
"""
import time

from django.conf import settings
from django.core import signing
from django.core.cache import cache

FORM_TOKEN_SALT = 'core.enquiry-form-started'
MIN_FILL_SECONDS = 3


def client_ip(request):
    # Render sits behind Cloudflare, which sets CF-Connecting-IP itself (clients cannot spoof it).
    cf_ip = request.META.get('HTTP_CF_CONNECTING_IP', '').strip()
    if cf_ip:
        return cf_ip
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def form_started_token():
    return signing.dumps(time.time(), salt=FORM_TOKEN_SALT)


def submitted_too_fast(token):
    """True only for a genuine token that was issued moments ago.

    Missing or unreadable tokens are allowed through (e.g. pages cached before this
    feature shipped); the honeypot and rate limit still apply to those.
    """
    if not token:
        return False
    try:
        started = signing.loads(token, salt=FORM_TOKEN_SALT, max_age=60 * 60 * 24)
    except (signing.BadSignature, TypeError, ValueError):
        return False
    return time.time() - float(started) < MIN_FILL_SECONDS


def rate_limit_exceeded(request):
    """Count this submission and report whether the IP is over its allowance."""
    limit, window = settings.ENQUIRY_RATE_LIMIT
    key = f'enquiry-rate:{client_ip(request)}'
    cache.add(key, 0, timeout=window)
    try:
        count = cache.incr(key)
    except ValueError:  # key expired between add() and incr()
        cache.set(key, 1, timeout=window)
        count = 1
    return count > limit
