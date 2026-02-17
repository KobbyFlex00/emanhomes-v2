from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError

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

# --- Team Member (Updated: Link Only) ---
class TeamMember(models.Model):
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    bio = models.TextField()
    
    # IMAGE UPLOAD REMOVED
    
    # LINK ONLY
    image_url = models.URLField(blank=True, null=True, help_text="Paste a link to a photo (e.g. LinkedIn profile pic).")
    
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
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='for_sale')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    location = models.CharField(max_length=200)
    description = models.TextField()
    
    # BED & BATH
    bedrooms = models.IntegerField(default=0, help_text="Number of bedrooms")
    bathrooms = models.IntegerField(default=0, help_text="Number of bathrooms")

    # MEDIA FIELDS (Image is Optional)
    main_image = models.ImageField(upload_to='properties/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True, help_text="Paste YouTube or Instagram link here")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def clean(self):
        # Validation: Must provide either an Image or a Video Link.
        if not self.main_image and not self.video_url:
            raise ValidationError("You must provide either an Image or a Video Link.")

    def get_embed_url(self):
        """
        Smartly converts YouTube AND Instagram links to Embed format.
        """
        if not self.video_url:
            return None
            
        # Handle YouTube
        if "youtube.com/watch?v=" in self.video_url:
            return self.video_url.replace("watch?v=", "embed/")
        elif "youtu.be/" in self.video_url:
            return self.video_url.replace("youtu.be/", "youtube.com/embed/")
            
        # Handle Instagram
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
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200, default="New Inquiry")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name}"