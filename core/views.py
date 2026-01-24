from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.core.mail import send_mail
from .models import Service, Property, ClientDocument, SiteConfiguration, TeamMember
from .forms import ContactForm

def home(request):
    services = Service.objects.all()
    properties = Property.objects.filter(status='available').order_by('-created_at')

    # --- SEARCH LOGIC ---
    query = request.GET.get('q')
    category = request.GET.get('category')

    if query:
        properties = properties.filter(
            Q(title__icontains=query) | 
            Q(location__icontains=query)
        )

    if category and category != 'all':
        properties = properties.filter(category=category)
    
    if not query and not category:
        properties = properties[:3]

    context = {
        'services': services,
        'properties': properties,
        'search_query': query, 
        'search_category': category,
    }
    return render(request, 'core/home.html', context)

def property_detail(request, slug):
    property = get_object_or_404(Property, slug=slug)
    # We fetch site_config here so the phone number in the sidebar works
    site_config = SiteConfiguration.objects.first() 
    context = {
        'property': property,
        'site_config': site_config,
    }
    return render(request, 'core/property_detail.html', context)

def about(request):
    site_config = SiteConfiguration.objects.first()
    team_members = TeamMember.objects.all()
    
    context = {
        'site_config': site_config,
        'team_members': team_members,
    }
    return render(request, 'core/about.html', context)

# UPDATED CONTACT VIEW
def contact(request):
    site_config = SiteConfiguration.objects.first()
    
    # Check if a subject was passed in the URL (e.g. from "Request Documents" button)
    initial_subject = request.GET.get('subject', '')

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            full_message = f"New message from {name} ({email}):\n\n{message}"

            try:
                send_mail(
                    subject=f"Website Inquiry: {subject}",
                    message=full_message,
                    from_email='noreply@emanhomes.com',
                    recipient_list=['info@emanhomes.com'], 
                    fail_silently=False,
                )
                messages.success(request, "Your message has been sent successfully!")
                return redirect('contact')
            except Exception as e:
                messages.error(request, "Error sending message. Please try again.")
    else:
        # Pre-fill the form with the subject if it exists
        form = ContactForm(initial={'subject': initial_subject})

    context = {
        'form': form,
        'site_config': site_config
    }
    return render(request, 'core/contact.html', context)

@login_required(login_url='login')
def client_portal(request):
    documents = ClientDocument.objects.filter(user=request.user).order_by('-uploaded_at')
    context = {
        'documents': documents
    }
    return render(request, 'core/portal.html', context)