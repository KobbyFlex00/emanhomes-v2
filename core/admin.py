from django.contrib import admin
from .models import SiteConfiguration, TeamMember, Service, Property, ContactMessage

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
    list_display = ('title', 'price', 'status', 'category', 'location')
    list_filter = ('status', 'category') # Filter by Sold/Rent/Sale
    search_fields = ('title', 'location')

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at')
    ordering = ('-created_at',)