from django.db import models
from django.utils.text import slugify

# --- Site Configuration (REAL EmanHomes Defaults) ---
class SiteConfiguration(models.Model):
    site_name = models.CharField(max_length=200, default="EmanHomes")
    main_phone = models.CharField(max_length=50, default="+233 20 584 3775")
    email = models.EmailField(default="emanpages@gmail.com")
    address = models.TextField(default="Dzen-Ayor, East Legon, Accra, Ghana")
    
    # Social Media
    facebook = models.URLField(blank=True, null=True, default="https://www.facebook.com/emanhomes")
    instagram = models.URLField(blank=True, null=True, default="https://www.instagram.com/emanhomes")
    twitter = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)

    def __str__(self):
        return "Site Configuration"

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

# --- Team Member ---
class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    bio = models.TextField()
    image = models.ImageField(upload_to='team/')
    
    def __str__(self):
        return self.name

# --- Service ---
class Service(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    icon_name = models.CharField(max_length=50, help_text="FontAwesome icon class (e.g., fas fa-home)")

    def __str__(self):
        return self.title

# --- Property (Updated with Realtor.com Status Features) ---
class Property(models.Model):
    CATEGORY_CHOICES = (
        ('land', 'Land'),
        ('residential', 'Residential House'),
        ('commercial', 'Commercial Property'),
    )
    
    # New: Professional Status Badges
    STATUS_CHOICES = (
        ('for_sale', 'For Sale'),
        ('for_rent', 'For Rent'),
        ('sold', 'Sold'),
    )
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='for_sale') # New Field
    price = models.DecimalField(max_digits=12, decimal_places=2)
    location = models.CharField(max_length=200)
    description = models.TextField()
    main_image = models.ImageField(upload_to='properties/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Properties"

# --- Contact Message (Database Backup for Emails) ---
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200, default="New Inquiry")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name}"