from django.db import models
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.contrib.auth.models import User

# 1. Site Configuration
class SiteConfiguration(models.Model):
    site_name = models.CharField(max_length=100, default="EmanHomes")
    main_phone = models.CharField(max_length=20, help_text="The primary number shown in the header")
    main_email = models.EmailField(help_text="The primary email shown in the header")
    office_location = models.CharField(max_length=255, default="East Legon, Accra")
    facebook_link = models.URLField(blank=True)
    instagram_link = models.URLField(blank=True)

    def save(self, *args, **kwargs):
        if not self.pk and SiteConfiguration.objects.exists():
            raise ValidationError('There can be only one Site Configuration instance')
        return super(SiteConfiguration, self).save(*args, **kwargs)

    def __str__(self):
        return "Site Configuration"

    class Meta:
        verbose_name = "Site Configuration"

# 2. Service Model
class Service(models.Model):
    title = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon_name = models.CharField(max_length=50, help_text="FontAwesome class (e.g. fas fa-home)", blank=True)
    description = models.TextField()
    image = models.ImageField(upload_to='services/', blank=True)
    
    def __str__(self):
        return self.title

# 3. Property Model
class Property(models.Model):
    CATEGORY_CHOICES = [
        ('land', 'Land Sales'),
        ('residential', 'Residential Housing'),
        ('commercial', 'Commercial Construction'),
    ]
    
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('sold', 'Sold'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    location = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    
    description = models.TextField()
    main_image = models.ImageField(upload_to='properties/')
    is_registered = models.BooleanField(default=False, help_text="Check if Indenture/Title is ready")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Properties"

    def __str__(self):
        return self.title

# 4. Client Document Model
class ClientDocument(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=100, help_text="e.g., Indenture, Site Plan, Receipt")
    document_file = models.FileField(upload_to='client_docs/')
    property_ref = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"

# 5. Team Member Model (NEW)
class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100, help_text="e.g. CEO, Lead Surveyor")
    image = models.ImageField(upload_to='team/')
    bio = models.TextField(blank=True, help_text="Short description of expertise")
    display_order = models.IntegerField(default=0, help_text="Lower numbers show first")

    class Meta:
        ordering = ['display_order']

    def __str__(self):
        return f"{self.name} - {self.role}"