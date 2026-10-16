import json

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


class CaptureNode(template.Node):
    def __init__(self, nodelist, var_name):
        self.nodelist = nodelist
        self.var_name = var_name

    def render(self, context):
        # The nodelist output is already escaped template output.
        context[self.var_name] = mark_safe(' '.join(self.nodelist.render(context).split()))
        return ''


@register.tag
def capture(parser, token):
    """{% capture as name %}...{% endcapture %} renders once into a variable.

    Lets one {% block %} (for example the page description) feed several meta tags.
    """
    bits = token.split_contents()
    if len(bits) != 3 or bits[1] != 'as':
        raise template.TemplateSyntaxError("Usage: {% capture as variable %}...{% endcapture %}")
    nodelist = parser.parse(('endcapture',))
    parser.delete_first_token()
    return CaptureNode(nodelist, bits[2])


@register.filter
def absolute_url(url):
    """Prefix site-relative URLs (local media and static files) with the canonical site URL."""
    url = str(url or '')
    return f"{settings.SITE_URL}{url}" if url.startswith('/') else url


@register.filter
def jsonld(data):
    """Serialise structured data for a <script type="application/ld+json"> block safely."""
    text = json.dumps(data, ensure_ascii=False)
    return mark_safe(text.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026'))
