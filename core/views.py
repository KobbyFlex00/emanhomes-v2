from django.shortcuts import render, get_object_or_404, redirect
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .models import Property, Service, TeamMember

def home(request):
    query = request.GET.get('q')
    category = request.GET.get('category')

    properties = Property.objects.filter(is_featured=True)

    if query:
        properties = properties.filter(location__icontains=query)
    
    if category and category != 'all':
        properties = properties.filter(category=category)

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

    properties = Property.objects.all()

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
        message = request.POST.get('message')

        
        subject = f"New Inquiry from {name} (EmanHomes)"
        full_message = f"Sender Name: {name}\nSender Email: {email}\n\nMessage:\n{message}"

        try:
            
            send_mail(
                subject,
                full_message,
                settings.EMAIL_HOST_USER,  
                ['emanpages@gmail.com'],  
                fail_silently=False,
            )
            messages.success(request, "Message sent successfully! We will get back to you soon.")
            return redirect('contact')
        except Exception as e:
            messages.error(request, f"Error sending message: {e}")
            
    return render(request, 'core/contact.html')