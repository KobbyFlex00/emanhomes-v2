from django.contrib import admin

from .models import ContactMessage, Property, PropertyImage, Service, SiteConfiguration, TeamMember


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return True

admin.site.register(TeamMember)
admin.site.register(Service)

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'title', 'price', 'status', 'category', 'location', 'is_featured')
    list_filter = ('status', 'category', 'is_featured')
    search_fields = ('reference_number', 'title', 'location', 'description')


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1


PropertyAdmin.inlines = [PropertyImageInline]

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'inquiry_type', 'lead_status', 'preferred_contact', 'property', 'follow_up_at', 'created_at')
    list_filter = ('lead_status', 'inquiry_type', 'preferred_contact', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message', 'property__title')
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at')
    ordering = ('-created_at',)
