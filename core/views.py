import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .forms import ContactForm
from .models import LegalPage, Property, Service, TeamMember
from .spam import client_ip, form_started_token, rate_limit_exceeded

logger = logging.getLogger(__name__)


@never_cache
@require_safe
def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        logger.exception('Health check database query failed')
        return JsonResponse({'status': 'error'}, status=503)
    return JsonResponse({'status': 'ok'})


MAX_PRICE_FILTER = Decimal('9999999999.99')  # largest value Property.price can hold


def _decimal_param(value):
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number < 0:
        return None
    return min(number, MAX_PRICE_FILTER)


def _int_param(value):
    # ASCII digits only: str.isdigit() also accepts characters such as '²' that int() rejects.
    return int(value) if value.isascii() and value.isdigit() and len(value) <= 3 else None


def filter_properties(request):
    properties = Property.objects.public().available_first()
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    status = request.GET.get('status', '').strip()
    min_price = _decimal_param(request.GET.get('min_price', '').strip())
    max_price = _decimal_param(request.GET.get('max_price', '').strip())
    bedrooms = _int_param(request.GET.get('bedrooms', '').strip())

    if query:
        properties = properties.filter(
            Q(title__icontains=query) |
            Q(location__icontains=query) |
            Q(description__icontains=query) |
            Q(reference_number__iexact=query)
        )
    if category and category != 'all':
        properties = properties.filter(category=category)
    if status and status != 'all':
        properties = properties.filter(status=status)
    if min_price is not None:
        properties = properties.filter(price__gte=min_price)
    if max_price is not None:
        properties = properties.filter(price__lte=max_price)
    if bedrooms is not None:
        properties = properties.filter(bedrooms__gte=bedrooms)
    return properties

def home(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    properties = filter_properties(request).prefetch_related('gallery')[:6]
    services = Service.objects.all()
    public_properties = Property.objects.public()
    categories = [
        {
            'key': key,
            'label': label,
            'count': public_properties.filter(category=key).count(),
        }
        for key, label in Property.CATEGORY_CHOICES
    ]

    context = {
        'properties': properties,
        'services': services,
        'search_query': query,
        'search_category': category,
        'categories': categories,
    }
    return render(request, 'core/home.html', context)

def about(request):
    team_members = TeamMember.objects.all()
    return render(request, 'core/about.html', {'team_members': team_members})

def properties_list(request):
    properties = Paginator(filter_properties(request), 9).get_page(request.GET.get('page'))

    context = {
        'properties': properties,
        'search_query': request.GET.get('q', ''),
        'search_category': request.GET.get('category', ''),
        'search_status': request.GET.get('status', ''),
        'search_min_price': request.GET.get('min_price', ''),
        'search_max_price': request.GET.get('max_price', ''),
        'search_bedrooms': request.GET.get('bedrooms', ''),
        'query_string': urlencode({key: value for key, value in request.GET.items() if key != 'page' and value}),
    }
    return render(request, 'core/properties.html', context)

def property_detail(request, slug):
    property = get_object_or_404(Property.objects.public().prefetch_related('gallery'), slug=slug)
    related_properties = Property.objects.public().filter(
        category=property.category, status__in=('for_sale', 'for_rent')
    ).exclude(pk=property.pk).order_by('-created_at')[:3]
    return render(request, 'core/property_detail.html', {
        'property': property, 'related_properties': related_properties,
        'enquiry_token': form_started_token(),
    })


def _single_line(value):
    return ' '.join(str(value).split())


def notify_staff_of_enquiry(request, inquiry):
    """Email staff about a saved enquiry. Never raises: the enquiry is already stored."""
    lines = [
        f"Name: {inquiry.name}",
        f"Email: {inquiry.email}",
        f"Phone: {inquiry.phone or '-'}",
        f"Type: {inquiry.get_inquiry_type_display()}",
        f"Preferred contact: {inquiry.get_preferred_contact_display()}",
    ]
    if inquiry.property:
        listing_url = request.build_absolute_uri(reverse('property_detail', args=[inquiry.property.slug]))
        lines += [
            f"Property: {inquiry.property.title} ({inquiry.property.reference_number})",
            f"Listing: {listing_url}",
        ]
    admin_url = request.build_absolute_uri(reverse('admin:core_contactmessage_change', args=[inquiry.pk]))
    lines += [f"Admin: {admin_url}", "", "Message:", inquiry.message]
    about = f" about {inquiry.property.title}" if inquiry.property else ""
    subject = _single_line(f"New enquiry from {inquiry.name}{about} (EmanHomes)")[:200]
    try:
        send_mail(
            subject,
            "\n".join(lines),
            settings.EMAIL_HOST_USER,
            [settings.LEAD_NOTIFICATION_EMAIL],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception("Lead notification failed for enquiry %s", inquiry.pk)
        inquiry.notification_error = f"{type(exc).__name__} at {timezone.now():%Y-%m-%d %H:%M} UTC"[:255]
        inquiry.save(update_fields=['notification_error'])
    else:
        inquiry.notification_sent_at = timezone.now()
        inquiry.save(update_fields=['notification_sent_at'])


def contact(request):
    property_slug = request.GET.get('property')
    related_property = Property.objects.public().filter(slug=property_slug).first() if property_slug else None
    if request.method == 'POST':
        form = ContactForm(request.POST)
        valid = form.is_valid()
        if rate_limit_exceeded(request):
            logger.warning('Enquiry rate limit exceeded for %s', client_ip(request))
            form.add_error(None, 'We have received several enquiries from your connection in a short time. '
                                 'Please wait a few minutes, or call or WhatsApp us directly.')
            return render(request, 'core/contact.html',
                          {'form': form, 'related_property': related_property}, status=429)
        if valid:
            if form.is_likely_spam:
                # Look successful so bots learn nothing; save and email nothing.
                logger.info('Discarded likely spam enquiry from %s', client_ip(request))
                return redirect('enquiry_thanks')
            inquiry = form.save(commit=False)
            inquiry.property = related_property
            inquiry.source = form.cleaned_data.get('source') or 'website'
            inquiry.save()
            notify_staff_of_enquiry(request, inquiry)
            return redirect('enquiry_thanks')
    else:
        initial = {}
        if related_property:
            initial = {
                'subject': f'Inquiry about {related_property.title}',
                'message': f'I am interested in {related_property.title} in {related_property.location}.',
                'inquiry_type': 'property',
            }
        if request.GET.get('type') == 'listing':
            initial.update({
                'subject': 'Property listing consultation',
                'inquiry_type': 'listing',
                'message': 'I would like to discuss listing a property with EmanHomes.',
            })
        initial['form_started'] = form_started_token()
        form = ContactForm(initial=initial)
    return render(request, 'core/contact.html', {'form': form, 'related_property': related_property})


def enquiry_thanks(request):
    return render(request, 'core/enquiry_thanks.html')


def legal_page(request, slug):
    page = get_object_or_404(LegalPage, slug=slug)
    if not page.is_published and not request.user.is_staff:
        # Drafts are not legally approved: the public must not see them.
        raise Http404
    return render(request, 'core/legal_page.html', {'page': page})
