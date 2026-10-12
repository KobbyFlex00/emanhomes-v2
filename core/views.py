from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.http import urlencode
import logging
from .forms import ContactForm
from .models import Property, Service, TeamMember, ContactMessage

logger = logging.getLogger(__name__)


def filter_properties(request):
    properties = Property.objects.all().order_by('-is_featured', '-created_at')
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    status = request.GET.get('status', '').strip()
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    bedrooms = request.GET.get('bedrooms', '').strip()

    if query:
        properties = properties.filter(
            Q(title__icontains=query) |
            Q(location__icontains=query) |
            Q(description__icontains=query)
        )
    if category and category != 'all':
        properties = properties.filter(category=category)
    if status and status != 'all':
        properties = properties.filter(status=status)
    if min_price:
        properties = properties.filter(price__gte=min_price)
    if max_price:
        properties = properties.filter(price__lte=max_price)
    if bedrooms:
        properties = properties.filter(bedrooms__gte=bedrooms)
    return properties

def home(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    properties = filter_properties(request)[:6]
    services = Service.objects.all()
    categories = []
    for key, label in Property.CATEGORY_CHOICES:
        category_property = Property.objects.filter(
            category=key,
        ).exclude(main_image='').first()
        categories.append({
            'key': key,
            'label': label,
            'count': Property.objects.filter(category=key).count(),
            'image_url': category_property.main_image.url if category_property else '',
        })
    hero_property = Property.objects.exclude(main_image='').first()
    
    context = {
        'properties': properties,
        'services': services,
        'search_query': query,
        'search_category': category,
        'categories': categories,
        'hero_property': hero_property,
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
    property = get_object_or_404(Property, slug=slug)
    related_properties = Property.objects.filter(
        category=property.category, status__in=('for_sale', 'for_rent')
    ).exclude(pk=property.pk).order_by('-created_at')[:3]
    return render(request, 'core/property_detail.html', {
        'property': property, 'related_properties': related_properties
    })

def contact(request):
    property_slug = request.GET.get('property')
    related_property = Property.objects.filter(slug=property_slug).first() if property_slug else None
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.property = related_property
            inquiry.source = request.POST.get('source', 'website')
            inquiry.save()
            full_message = (
                f"Sender: {inquiry.name}\nEmail: {inquiry.email}\n"
                f"Type: {inquiry.get_inquiry_type_display()}\n"
                f"Preferred contact: {inquiry.get_preferred_contact_display()}\n\n"
                f"Message:\n{inquiry.message}"
            )
            try:
                send_mail(
                    f"New inquiry from {inquiry.name} (EmanHomes)",
                    full_message,
                    settings.EMAIL_HOST_USER,
                    [settings.LEAD_NOTIFICATION_EMAIL],
                    fail_silently=False,
                )
            except (OSError, ValueError):
                logger.exception("Lead notification failed for inquiry %s", inquiry.pk)
                messages.warning(request, "Your enquiry was saved, but notification delivery is delayed.")
            else:
                messages.success(request, "Thank you. Your enquiry has been sent successfully.")
            return redirect('contact')
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
        form = ContactForm(initial=initial)
    return render(request, 'core/contact.html', {'form': form, 'related_property': related_property})