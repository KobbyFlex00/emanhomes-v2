from django.contrib import admin
from .models import SiteConfiguration, Service, Property, ClientDocument, TeamMember

@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'icon_name')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'location', 'status', 'is_registered')
    list_filter = ('category', 'status', 'is_registered')
    search_fields = ('title', 'location')

@admin.register(ClientDocument)
class ClientDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'property_ref', 'uploaded_at')
    list_filter = ('user', 'uploaded_at')
    search_fields = ('title', 'user__username')
    autocomplete_fields = ['user', 'property_ref']

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'display_order')
    list_editable = ('display_order',)