from django.contrib import admin
from .models import SiteConfiguration, TeamMember, Service, Property, ContactMessage

@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Only allow 1 config
        if self.model.objects.exists():
            return False
        return True

admin.site.register(TeamMember)
admin.site.register(Service)
admin.site.register(Property)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at')
    ordering = ('-created_at',)