from django.contrib import admin
from django.utils.html import format_html
from .models import Rule, Event
from django.urls import reverse


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "device_metric", "rule_status", "last_triggered")
    list_filter = ("is_active", "device_metric")
    search_fields = (
        "name",
        "description",
        "device_metric__device__name",
        "device_metric__metric__metric_type",
    )
    readonly_fields = ("id", "last_triggered")

    @admin.display(description="Status", boolean=True)
    def rule_status(self, obj):
        return obj.is_active

    @admin.display(description="Last Triggered")
    def last_triggered(self, obj):
        from django.db.models import Max

        latest = Event.objects.filter(rule=obj).aggregate(Max("timestamp"))["timestamp__max"]
        if latest:
            return latest
        return format_html('<span style="color: gray;">{}</span>', 'Never')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_select_related = ("rule__device_metric__device",)
    
    list_display = (
        "id",
        "rule_link",
        "acknowledged",
        "timestamp",
        "created_at",
        "telemetry_link",
        "device_link",
    )
    
    list_filter = ("timestamp", "created_at", "rule", "acknowledged")
    search_fields = ("id", "rule__name", "rule__device_metric__device__name", "trigger_telemetry_id")
    readonly_fields = ("id", "timestamp", "created_at")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)
    actions = ["mark_acknowledged", "mark_unacknowledged"]

    @admin.display(description="Device ID", ordering="trigger_device_id")
    def device_link(self, obj):
        if obj.trigger_device_id:
            url = reverse("admin:devices_device_change", args=[obj.trigger_device_id])
            return format_html('<a href="{}">#{}</a>', url, obj.trigger_device_id)
        return "-"

    @admin.display(description="Rule", ordering="rule__name")
    def rule_link(self, obj):
        if obj.rule:
            url = reverse("admin:rules_rule_change", args=[obj.rule.id])
            return format_html('<a href="{}">{}</a>', url, obj.rule.name)
        return "-"

    @admin.display(description="Telemetry ID", ordering="trigger_telemetry_id")
    def telemetry_link(self, obj):
        if obj.trigger_telemetry_id:
            url = reverse("admin:devices_telemetry_change", args=[obj.trigger_telemetry_id])
            return format_html('<a href="{}">#{}</a>', url, obj.trigger_telemetry_id)
        return obj.trigger_telemetry_id

    @admin.action(description="Mark selected events as acknowledged")
    def mark_acknowledged(self, request, queryset):
        if not request.user.has_perm("rules.change_event"):
            self.message_user(request, "Permission denied.", level="error")
            return

        try:
            updated = queryset.update(acknowledged=True)
        except Exception as exc:
            self.message_user(request, f"Failed to acknowledge events: {exc}", level="error")
            return

        self.message_user(request, f"{updated} event(s) marked as acknowledged.")

    @admin.action(description="Mark selected events as unacknowledged")
    def mark_unacknowledged(self, request, queryset):
        if not request.user.has_perm("rules.change_event"):
            self.message_user(request, "Permission denied.", level="error")
            return

        try:
            updated = queryset.update(acknowledged=False)
        except Exception as exc:
            self.message_user(request, f"Failed to unacknowledge events: {exc}", level="error")
            return

        self.message_user(request, f"{updated} event(s) marked as unacknowledged.")
