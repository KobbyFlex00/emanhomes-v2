import logging

import cloudinary.exceptions
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponseRedirect
from django.utils.html import format_html

from .models import (
    Article,
    ContactMessage,
    LegalPage,
    Property,
    PropertyImage,
    Service,
    SiteConfiguration,
    TeamMember,
)

logger = logging.getLogger(__name__)


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Company', {'fields': ('site_name', 'address', 'business_hours')}),
        ('Homepage', {'fields': ('hero_headline', 'hero_subheadline')}),
        ('Contact', {'fields': ('main_phone', 'secondary_phone', 'whatsapp_phone', 'email')}),
        ('Social profiles', {'fields': ('facebook', 'instagram', 'twitter', 'linkedin', 'tiktok', 'youtube', 'linktree')}),
        ('History', {'fields': ('updated_at',)}),
    )
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(TeamMember)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')


class PropertyImageInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        listing = self.instance
        if listing.main_image or listing.video_url:
            return
        has_gallery_photo = any(
            form.cleaned_data.get('image') and not form.cleaned_data.get('DELETE')
            for form in self.forms if hasattr(form, 'cleaned_data')
        )
        if not has_gallery_photo:
            raise ValidationError('Add a main image, a gallery photo or a video link.')


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    formset = PropertyImageInlineFormSet
    extra = 1
    fields = ('preview', 'image', 'alt_text', 'caption', 'display_order')
    readonly_fields = ('preview',)

    @admin.display(description='Preview')
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html('<img src="{}" alt="" style="height:60px;border-radius:4px">', obj.image.url)
        return '-'


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    def changeform_view(self, request, *args, **kwargs):
        # Uploads go to Cloudinary while saving. If it refuses them, the save is rolled
        # back; tell staff why instead of showing the generic error page.
        try:
            return super().changeform_view(request, *args, **kwargs)
        except cloudinary.exceptions.Error:
            logger.exception('Image upload to Cloudinary failed in the property admin')
            self.message_user(
                request,
                'The image storage service rejected the upload, so nothing was saved. '
                'Ask the site administrator to run "python manage.py check_media_storage".',
                messages.ERROR,
            )
            return HttpResponseRedirect(request.get_full_path())

    list_display = (
        'reference_number', 'title', 'price_display', 'status', 'publication_status',
        'category', 'location', 'is_featured', 'updated_at',
    )
    list_editable = ('status', 'publication_status', 'is_featured')
    list_filter = ('publication_status', 'status', 'category', 'is_featured', 'currency')
    search_fields = ('reference_number', 'title', 'location', 'description')
    readonly_fields = ('reference_number', 'created_at', 'updated_at')
    inlines = [PropertyImageInline]
    actions = ('publish', 'unpublish_to_draft', 'archive', 'mark_sold', 'mark_rented')
    fieldsets = (
        ('Listing', {'fields': (
            'title', 'slug', 'reference_number', 'category', 'status', 'publication_status', 'is_featured',
        )}),
        ('Price', {'fields': ('currency', 'price')}),
        ('Details', {'fields': (
            'location', 'description', 'bedrooms', 'bathrooms',
            'property_size', 'property_size_unit', 'amenities',
        )}),
        ('Media', {'fields': ('main_image', 'video_url')}),
        ('Search engines', {'classes': ('collapse',), 'fields': ('seo_title', 'seo_description')}),
        ('History', {'fields': ('created_at', 'updated_at')}),
    )

    @admin.display(description='Price', ordering='price')
    def price_display(self, obj):
        return obj.price_display

    def _bulk_update(self, request, queryset, message, **changes):
        # Save each object so updated_at changes.
        for obj in queryset:
            for field, value in changes.items():
                setattr(obj, field, value)
            obj.save(update_fields=[*changes, 'updated_at'])
        self.message_user(request, f"{queryset.count()} listing(s) {message}.", messages.SUCCESS)

    @admin.action(description='Publish selected listings')
    def publish(self, request, queryset):
        self._bulk_update(request, queryset, 'published', publication_status=Property.PUBLISHED)

    @admin.action(description='Move selected listings to draft (hide)')
    def unpublish_to_draft(self, request, queryset):
        self._bulk_update(request, queryset, 'moved to draft', publication_status=Property.DRAFT)

    @admin.action(description='Archive selected listings (hide)')
    def archive(self, request, queryset):
        self._bulk_update(request, queryset, 'archived', publication_status=Property.ARCHIVED)

    @admin.action(description='Mark selected listings as Sold')
    def mark_sold(self, request, queryset):
        self._bulk_update(request, queryset, 'marked as sold', status='sold')

    @admin.action(description='Mark selected listings as Rented')
    def mark_rented(self, request, queryset):
        self._bulk_update(request, queryset, 'marked as rented', status='rented')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'phone', 'email', 'inquiry_type', 'lead_status', 'preferred_contact',
        'property', 'notified', 'follow_up_at', 'created_at',
    )
    list_filter = ('lead_status', 'inquiry_type', 'preferred_contact', 'created_at')
    search_fields = ('name', 'email', 'phone', 'subject', 'message', 'property__title', 'property__reference_number')
    readonly_fields = (
        'name', 'email', 'phone', 'subject', 'message', 'inquiry_type', 'preferred_contact',
        'property', 'source', 'consent_to_contact', 'notification_sent_at', 'notification_error', 'created_at',
    )
    list_select_related = ('property',)
    ordering = ('-created_at',)
    fieldsets = (
        ('Enquiry', {'fields': (
            'name', 'email', 'phone', 'preferred_contact', 'inquiry_type', 'property', 'subject', 'message',
        )}),
        ('Follow-up', {'fields': ('lead_status', 'follow_up_at', 'internal_notes')}),
        ('Record', {'fields': (
            'source', 'consent_to_contact', 'notification_sent_at', 'notification_error', 'created_at',
        )}),
    )

    @admin.display(description='Emailed', boolean=True)
    def notified(self, obj):
        if obj.notification_error:
            return False
        return bool(obj.notification_sent_at) or None

    def has_add_permission(self, request):
        # Enquiries come from the website forms; staff update their status here.
        return False


@admin.register(LegalPage)
class LegalPageAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'approval_note', 'updated_at')
    fields = ('slug', 'title', 'status', 'approval_note', 'body', 'updated_at')
    readonly_fields = ('slug', 'updated_at')

    def get_readonly_fields(self, request, obj=None):
        # Publishing makes legal wording public, so only superusers may change the status.
        if request.user.is_superuser:
            return self.readonly_fields
        return (*self.readonly_fields, 'status', 'approval_note')

    def has_add_permission(self, request):
        return False  # The privacy policy and terms pages are created by migration.

    def has_delete_permission(self, request, obj=None):
        return False

    def view_on_site(self, obj):
        return f'/{obj.slug}/'


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'published_at', 'author_display_name', 'updated_at')
    list_filter = ('status',)
    search_fields = ('title', 'excerpt', 'body')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
    actions = ('publish', 'unpublish')
    fieldsets = (
        (None, {'fields': ('title', 'slug', 'excerpt', 'body')}),
        ('Cover photo', {'fields': ('cover_image', 'cover_alt')}),
        ('Publishing', {'fields': ('status', 'published_at', 'author_display_name')}),
        ('Search engines', {'classes': ('collapse',), 'fields': ('seo_title', 'seo_description')}),
        ('History', {'fields': ('created_at', 'updated_at')}),
    )

    def view_on_site(self, obj):
        return f'/insights/{obj.slug}/'

    @admin.action(description='Publish selected articles')
    def publish(self, request, queryset):
        for article in queryset:
            article.status = Article.PUBLISHED
            article.save()
        self.message_user(request, f'{queryset.count()} article(s) published.', messages.SUCCESS)

    @admin.action(description='Move selected articles to draft (hide)')
    def unpublish(self, request, queryset):
        for article in queryset:
            article.status = Article.DRAFT
            article.save()
        self.message_user(request, f'{queryset.count()} article(s) moved to draft.', messages.SUCCESS)
