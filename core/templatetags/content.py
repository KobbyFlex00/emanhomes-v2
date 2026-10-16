from django import template
from django.utils.html import format_html_join
from django.utils.html import urlize as urlize_html
from django.utils.safestring import mark_safe

register = template.Library()


def _inline(text):
    # urlize escapes everything that is not a link it creates.
    return urlize_html(text, nofollow=True, autoescape=True)


@register.filter
def simple_format(text):
    """Render staff-entered plain text safely.

    '## ' / '### ' start headings, '- ' lines form a list, blank lines separate
    paragraphs. No raw HTML is ever passed through.
    """
    html = []
    for block in str(text).replace('\r\n', '\n').split('\n\n'):
        lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
        if not lines:
            continue
        if lines[0].startswith('### '):
            html.append(f'<h3>{_inline(lines[0][4:])}</h3>')
            lines = lines[1:]
        elif lines[0].startswith('## '):
            html.append(f'<h2>{_inline(lines[0][3:])}</h2>')
            lines = lines[1:]
        if not lines:
            continue
        if all(line.startswith('- ') for line in lines):
            items = format_html_join('', '<li>{}</li>', ((mark_safe(_inline(line[2:])),) for line in lines))
            html.append(f'<ul>{items}</ul>')
        else:
            html.append('<p>' + '<br>'.join(_inline(line) for line in lines) + '</p>')
    return mark_safe('\n'.join(html))
