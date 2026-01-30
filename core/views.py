from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .models import Property, Service, TeamMember, ContactMessage

def home(request):
    query = request.GET.get('q')
    category = request.GET.get('category')
    properties = Property.objects.all().order_by('-created_at')

    if query:
        properties = properties.filter(location__icontains=query)
    if category and category != 'all':
        properties = properties.filter(category=category)

    properties = properties[:6]
    services = Service.objects.all()
    
    context = {
        'properties': properties,
        'services': services,
        'search_query': query,
        'search_category': category
    }
    return render(request, 'core/home.html', context)

def about(request):
    team_members = TeamMember.objects.all()
    return render(request, 'core/about.html', {'team_members': team_members})

def properties_list(request):
    query = request.GET.get('q')
    category = request.GET.get('category')
    properties = Property.objects.all().order_by('-created_at')

    if query:
        properties = properties.filter(location__icontains=query)
    if category and category != 'all':
        properties = properties.filter(category=category)

    context = {
        'properties': properties,
        'search_query': query,
        'search_category': category
    }
    return render(request, 'core/properties.html', context)

def property_detail(request, slug):
    property = get_object_or_404(Property, slug=slug)
    return render(request, 'core/property_detail.html', {'property': property})

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message_text = request.POST.get('message')

        # 1. Save to Database (Admin Panel Backup)
        ContactMessage.objects.create(
            name=name,
            email=email,
            message=message_text
        )

        # 2. Send Email
        subject = f"New Inquiry from {name} (EmanHomes)"
        full_message = f"Sender Name: {name}\nSender Email: {email}\n\nMessage:\n{message_text}"

        try:
            send_mail(
                subject,
                full_message,
                settings.EMAIL_HOST_USER,
                ['emanpages@gmail.com'], # Real email
                fail_silently=False,
            )
            messages.success(request, "Message sent successfully! We will get back to you soon.")
        except Exception as e:
            # Show success anyway because we saved it to the database
            messages.success(request, "Message received! We will contact you shortly.")
            print(f"Email failed: {e}") # Log error for debugging
            
        return redirect('contact')
            
    return render(request, 'core/contact.html')