from django.db import models
from django.utils.text import slugify

# --- Site Configuration (Your existing model) ---
class SiteConfiguration(models.Model):
    site_name = models.CharField(max_length=200, default="EmanHomes")
    main_phone = models.CharField(max_length=50, default="+233 24 000 0000")
    email = models.EmailField(default="info@emanhomes.com")
    address = models.TextField(default="Accra, Ghana")
    facebook = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    instagram = models.URLField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)

    def __str__(self):
        return "Site Configuration"

    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"

# --- Team Member (Your existing model) ---
class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    bio = models.TextField()
    image = models.ImageField(upload_to='team/')
    
    def __str__(self):
        return self.name

# --- Service (Your existing model) ---
class Service(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    icon_name = models.CharField(max_length=50, help_text="FontAwesome icon class (e.g., fas fa-home)")

    def __str__(self):
        return self.title

# --- Property (Your existing model) ---
class Property(models.Model):
    CATEGORY_CHOICES = (
        ('land', 'Land'),
        ('residential', 'Residential House'),
        ('commercial', 'Commercial Property'),
    )
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    location = models.CharField(max_length=200)
    description = models.TextField()
    main_image = models.ImageField(upload_to='properties/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Simple fix for "is_featured" error: We just don't use it.
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Properties"

# --- NEW: Contact Message (Saves emails to Admin) ---
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200, default="New Inquiry")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name}"