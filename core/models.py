from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Now
from django.template.defaultfilters import floatformat
from django.utils.text import slugify

YOUTUBE_HOSTS = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'}
INSTAGRAM_HOSTS = {'instagram.com', 'www.instagram.com'}


# --- Site Configuration ---
class SiteConfiguration(models.Model):
    site_name = models.CharField(max_length=200, default="EmanHomes")
    main_phone = models.CharField(max_length=50, default="+233 20 584 3775")
    secondary_phone = models.CharField(max_length=50, default="+233 55 448 0444")
    whatsapp_phone = models.CharField(max_length=50, default="+233 20 584 3775")
    email = models.EmailField(default="emanpages@gmail.com")
    address = models.TextField(default="Dzen-Ayor, East Legon, Accra, Ghana")

    business_hours = models.CharField(
        max_length=100, default="Open 24 hours, 7 days a week", db_default="Open 24 hours, 7 days a week"
    )

    # Social Media
    facebook = models.URLField(blank=True, null=True, default="https://www.facebook.com/emanhomesofficial")
    instagram = models.URLField(blank=True, null=True, default="https://www.instagram.com/emanhomes")
    twitter = models.URLField("X (Twitter)", blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    tiktok = models.URLField("TikTok", blank=True, null=True, default="https://www.tiktok.com/@emanhomesltd")
    youtube = models.URLField("YouTube", blank=True, null=True)
    linktree = models.URLField("Linktree", blank=True, null=True, default="https://linktr.ee/emanhomes")
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())

    def __str__(self):
        return "Site Configuration"

    @property
    def whatsapp_number(self):
        """Digits only, as wa.me links require."""
        return ''.join(ch for ch in self.whatsapp_phone if ch.isdigit())

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
class PropertyQuerySet(models.QuerySet):
    def public(self):
        """Listings visitors may see. Sold/rented stay visible, marked as such."""
        return self.filter(publication_status=Property.PUBLISHED)

    def available_first(self):
        closed = models.Case(
            models.When(status__in=Property.CLOSED_STATUSES, then=1),
            default=0,
            output_field=models.IntegerField(),
        )
        return self.annotate(closed_rank=closed).order_by('closed_rank', '-is_featured', '-created_at', 'pk')


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
        ('rented', 'Rented'),
    )
    CLOSED_STATUSES = ('sold', 'rented')

    DRAFT, PUBLISHED, ARCHIVED = 'draft', 'published', 'archived'
    PUBLICATION_CHOICES = (
        (DRAFT, 'Draft (hidden)'),
        (PUBLISHED, 'Published'),
        (ARCHIVED, 'Archived (hidden)'),
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
    publication_status = models.CharField(
        max_length=20, choices=PUBLICATION_CHOICES, default=PUBLISHED, db_default=PUBLISHED, db_index=True,
        help_text="Only published listings appear on the website.",
    )
    is_featured = models.BooleanField(default=False)

    # CURRENCY FIELD ADDED HERE
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    price = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True,
        help_text='Leave blank to show "Contact for price".',
    )

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

    # SEO
    seo_title = models.CharField(
        max_length=70, blank=True, db_default='', help_text="Optional. Defaults to the title."
    )
    seo_description = models.CharField(
        max_length=160, blank=True, db_default='',
        help_text="Optional. Shown in search results; defaults to a summary.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())

    objects = PropertyQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        if not self.reference_number:
            self.reference_number = f"EH-{uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def _unique_slug(self):
        base = slugify(self.title)[:240] or 'property'
        slug, counter = base, 2
        while Property.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    def clean(self):
        if not self.main_image and not self.video_url:
            raise ValidationError("You must provide either an Image or a Video Link.")
        if self.price is not None and self.price < 0:
            raise ValidationError({'price': "Price cannot be negative."})
        if self.video_url and not self.get_embed_url():
            raise ValidationError({'video_url': "Use a YouTube video or an Instagram post/reel link."})

    @property
    def is_closed(self):
        return self.status in self.CLOSED_STATUSES

    @property
    def price_display(self):
        if self.price is None:
            return "Contact for price"
        return f"{self.currency_symbol}{intcomma(floatformat(self.price, -2))}"

    @property
    def currency_symbol(self):
        """Returns the correct symbol based on the selected currency."""
        return 'GH₵' if self.currency == 'GHS' else '$'

    def get_embed_url(self):
        """Embed URL for YouTube/Instagram links only; anything else is not embedded."""
        if not self.video_url:
            return None
        try:
            url = urlparse(self.video_url)
            host = (url.hostname or '').lower()
        except ValueError:
            return None
        parts = [part for part in url.path.split('/') if part]

        if host in YOUTUBE_HOSTS:
            if host == 'youtu.be' and parts:
                video_id = parts[0]
            elif parts[:1] == ['watch']:
                video_id = parse_qs(url.query).get('v', [''])[0]
            elif len(parts) >= 2 and parts[0] in ('embed', 'shorts', 'live'):
                video_id = parts[1]
            else:
                return None
            return f"https://www.youtube.com/embed/{video_id}" if video_id else None

        if host in INSTAGRAM_HOSTS and len(parts) >= 2 and parts[0] in ('p', 'reel', 'tv'):
            return f"https://www.instagram.com/{parts[0]}/{parts[1]}/embed"

        return None

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Properties"
        indexes = [
            models.Index(fields=['publication_status', 'status'], name='property_visibility_idx'),
            models.Index(fields=['category'], name='property_category_idx'),
            models.Index(fields=['-created_at'], name='property_created_idx'),
        ]

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
    phone = models.CharField(max_length=30, blank=True, db_default='')
    subject = models.CharField(max_length=200, default="New Inquiry")
    message = models.TextField()
    inquiry_type = models.CharField(max_length=20, choices=INQUIRY_CHOICES, default='general')
    preferred_contact = models.CharField(max_length=20, choices=CONTACT_METHOD_CHOICES, default='email')
    property = models.ForeignKey(
        Property, on_delete=models.SET_NULL, blank=True, null=True, related_name='inquiries'
    )
    source = models.CharField(max_length=100, blank=True)
    consent_to_contact = models.BooleanField(default=False)
    lead_status = models.CharField(max_length=20, choices=LEAD_STATUS_CHOICES, default='new')
    follow_up_at = models.DateTimeField(blank=True, null=True)
    internal_notes = models.TextField(blank=True)
    notification_sent_at = models.DateTimeField(blank=True, null=True)
    notification_error = models.CharField(max_length=255, blank=True, db_default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Enquiry"
        verbose_name_plural = "Enquiries"
        ordering = ('-created_at',)

    def __str__(self):
        return f"Message from {self.name}"


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='properties/gallery/')
    alt_text = models.CharField(
        max_length=200, blank=True, db_default='', help_text="Describe the photo for screen readers, e.g. 'Front view of the house'."
    )
    caption = models.CharField(max_length=200, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('display_order', 'id')

    def __str__(self):
        return f"{self.property.title} image"


class LegalPage(models.Model):
    PRIVACY, TERMS = 'privacy', 'terms'
    SLUG_CHOICES = ((PRIVACY, 'Privacy policy'), (TERMS, 'Terms of use'))
    DRAFT, PUBLISHED = 'draft', 'published'
    STATUS_CHOICES = (
        (DRAFT, 'Draft (staff only, not legally approved)'),
        (PUBLISHED, 'Published (legally approved)'),
    )

    slug = models.SlugField(choices=SLUG_CHOICES, unique=True)
    title = models.CharField(max_length=120)
    body = models.TextField(
        help_text="Plain text. Start a line with '## ' for a heading or '- ' for a bullet; "
                  "leave a blank line between paragraphs.",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=DRAFT, db_default=DRAFT,
        help_text="Publish only after a Ghana-qualified lawyer has approved the wording.",
    )
    approval_note = models.CharField(
        max_length=200, blank=True, db_default='',
        help_text="Who approved this version and when, e.g. 'Approved by <lawyer>, 12 Nov 2026'.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('slug',)

    def __str__(self):
        return self.title

    @property
    def is_published(self):
        return self.status == self.PUBLISHED
