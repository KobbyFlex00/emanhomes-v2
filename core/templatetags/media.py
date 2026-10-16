"""Responsive photo URLs.

Cloudinary resizes and compresses on request when the delivery URL carries a
transformation, so phones download a small image instead of the full upload:
    https://res.cloudinary.com/<cloud>/image/upload/f_auto,q_auto,c_limit,w_800/v1/media/x.jpg
Non-Cloudinary URLs (local media in development, static files) are returned unchanged.
"""
from django import template
from django.utils.html import format_html_join

register = template.Library()

UPLOAD_MARKER = '/image/upload/'
SRCSET_WIDTHS = (400, 800, 1200)


def cloudinary_variant(url, width):
    url = str(url or '')
    if 'res.cloudinary.com' not in url or UPLOAD_MARKER not in url:
        return url
    head, tail = url.split(UPLOAD_MARKER, 1)
    return f'{head}{UPLOAD_MARKER}f_auto,q_auto,c_limit,w_{int(width)}/{tail}'


@register.filter
def resized(url, width):
    """{{ url|resized:800 }}: a Cloudinary copy at most 800px wide (others unchanged)."""
    return cloudinary_variant(url, width)


@register.simple_tag
def responsive_srcset(url):
    """srcset="..." for Cloudinary photos; empty for other URLs (the plain src is used)."""
    url = str(url or '')
    if cloudinary_variant(url, 1) == url:
        return ''
    return format_html_join(', ', '{} {}w', ((cloudinary_variant(url, w), w) for w in SRCSET_WIDTHS))
