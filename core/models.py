from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from uuid import uuid4

# --- Site Configuration ---
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
    image_url = models.URLField(blank=True, null=True, help_text="Paste a direct link to a .jpg/.png photo (e.g., Right-click LinkedIn photo > Copy Image Address). Google Drive 'view' links will NOT work.")
    
    def __str__(self):
        return self.name

# --- Service ---
class Service(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    icon_name = models.CharField(max_length=50, help_text="FontAwesome icon class (e.g., fas fa-home)")

    def __str__(self):
        return self.title

# --- Property ---
class Property(models.Model):
    CATEGORY_CHOICES = (
        ('land', 'Land'),
        ('residential', 'Residential House'),
        ('commercial', 'Commercial Property'),
    )
    
    STATUS_CHOICES = (
        ('for_sale', 'For Sale'),
        ('for_rent', 'For Rent'),
        ('sold', 'Sold'),
    )

    # NEW: CURRENCY CHOICES
    CURRENCY_CHOICES = (
        ('USD', 'USD ($)'),
        ('GHS', 'GHS (GH₵)'),
    )
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    reference_number = models.CharField(max_length=30, unique=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='for_sale')
    is_featured = models.BooleanField(default=False)
    
    # CURRENCY FIELD ADDED HERE
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    
    location = models.CharField(max_length=200)
    description = models.TextField()
    property_size = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    property_size_unit = models.CharField(max_length=20, blank=True, default='sq ft')
    amenities = models.TextField(blank=True, help_text="One amenity per line")
    
    # BED & BATH
    bedrooms = models.IntegerField(default=0, help_text="Number of bedrooms")
    bathrooms = models.IntegerField(default=0, help_text="Number of bathrooms")

    # MEDIA FIELDS
    main_image = models.ImageField(upload_to='properties/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True, help_text="Paste YouTube or Instagram link here")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if not self.reference_number:
            self.reference_number = f"EH-{uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def clean(self):
        if not self.main_image and not self.video_url:
            raise ValidationError("You must provide either an Image or a Video Link.")

    @property
    def currency_symbol(self):
        """Returns the correct symbol based on the selected currency."""
        return 'GH₵' if self.currency == 'GHS' else '$'

    def get_embed_url(self):
        if not self.video_url:
            return None
            
        if "youtube.com/watch?v=" in self.video_url:
            return self.video_url.replace("watch?v=", "embed/")
        elif "youtu.be/" in self.video_url:
            return self.video_url.replace("youtu.be/", "youtube.com/embed/")
            
        elif "instagram.com/p/" in self.video_url or "instagram.com/reel/" in self.video_url:
            clean_url = self.video_url.split('?')[0]
            if not clean_url.endswith('/embed'):
                if clean_url.endswith('/'):
                    return clean_url + "embed"
                else:
                    return clean_url + "/embed"
            return clean_url
            
        return self.video_url

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Properties"

# --- Contact Message ---
class ContactMessage(models.Model):
    LEAD_STATUS_CHOICES = (
        ('new', 'New'),
        ('in_progress', 'In progress'),
        ('qualified', 'Qualified'),
        ('closed', 'Closed'),
    )
    INQUIRY_CHOICES = (
        ('general', 'General enquiry'),
        ('property', 'Property enquiry'),
        ('viewing', 'Request a viewing'),
        ('listing', 'List or sell a property'),
    )
    CONTACT_METHOD_CHOICES = (
        ('whatsapp', 'WhatsApp'),
        ('phone', 'Phone'),
        ('email', 'Email'),
    )

    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200, default="New Inquiry")
    message = models.TextField()
    inquiry_type = models.CharField(max_length=20, choices=INQUIRY_CHOICES, default='general')
    preferred_contact = models.CharField(max_length=20, choices=CONTACT_METHOD_CHOICES, default='email')
    property = models.ForeignKey(
        Property, on_delete=models.SET_NULL, blank=True, null=True, related_name='inquiries'
    )
    source = models.CharField(max_length=100, blank=True)
    consent_to_contact = models.BooleanField(default=True)
    lead_status = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES, default='new')
    follow_up_at = models.DateTimeField(blank=True, null=True)
    internal_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name}"


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='properties/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('display_order', 'id')

    def __str__(self):
        return f"{self.property.title} image"