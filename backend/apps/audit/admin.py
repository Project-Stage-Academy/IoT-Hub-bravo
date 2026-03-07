import json

from django.contrib import admin
from django.utils.safestring import mark_safe

from apps.audit.models.audit_log import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'occurred_at',
        'severity',
        'event_type',
        'entity_type',
        'entity_id',
        'actor_type',
        'actor_id',
    )
    list_filter = ('event_type', 'entity_type', 'severity', 'actor_type')
    search_fields = ('event_type', 'entity_id', 'actor_id')
    date_hierarchy = 'occurred_at'

    fieldsets = (
        ('Audit', {'fields': ('id', 'audit_event_id')}),
        ('Actor', {'fields': ('actor_type', 'actor_id')}),
        ('Entity', {'fields': ('entity_type', 'entity_id')}),
        ('Event', {'fields': ('event_type', 'severity', 'occurred_at', 'details_pretty')}),
    )

    def details_pretty(self, obj):
        pretty = json.dumps(obj.details, ensure_ascii=False, indent=2, sort_keys=True)
        return mark_safe(f'<pre style="white-space: pre-wrap">{pretty}</pre>')

    details_pretty.short_description = 'Details'

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ('id',)
        return (
            'id',
            'audit_event_id',
            'actor_type',
            'actor_id',
            'entity_type',
            'entity_id',
            'event_type',
            'severity',
            'occurred_at',
            'details',
        )

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True
        return False
