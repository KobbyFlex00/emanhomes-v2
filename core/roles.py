"""Staff roles (Django groups) kept in sync with the permissions below.

Assign people to a group in Admin > Groups instead of making them superusers.
Runs after every `migrate`, so new deployments always have current roles.
"""
from django.contrib.auth.models import Group, Permission

ROLE_PERMISSIONS = {
    'Property managers': {
        'property': ('add', 'change', 'delete', 'view'),
        'propertyimage': ('add', 'change', 'delete', 'view'),
        'contactmessage': ('view',),
    },
    'Enquiry managers': {
        # No delete: enquiry history must be kept.
        'contactmessage': ('change', 'view'),
        'property': ('view',),
    },
    'Content editors': {
        'service': ('add', 'change', 'delete', 'view'),
        'teammember': ('add', 'change', 'delete', 'view'),
        'siteconfiguration': ('add', 'change', 'view'),
        'article': ('add', 'change', 'delete', 'view'),
    },
}


def sync_staff_roles(**kwargs):
    for group_name, models in ROLE_PERMISSIONS.items():
        codenames = [f'{action}_{model}' for model, actions in models.items() for action in actions]
        permissions = Permission.objects.filter(content_type__app_label='core', codename__in=codenames)
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.set(permissions)
