from django.contrib import admin
from django.db.models import Max
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from .models import Rule, Event

from apps.devices.models import Telemetry


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

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _last_triggered=Max("event_set__timestamp")
        )

    @admin.display(description="Status", boolean=True)
    def rule_status(self, obj):
        return obj.is_active

    @admin.display(description="Last Triggered")
    def last_triggered(self, obj):
        latest = getattr(obj, "_last_triggered", None)
        if latest:
            return latest
        return format_html('<span style="color: gray;">{}</span>', "Never")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "rule",
        "rule_device",
        "acknowledged",
        "timestamp",
        "created_at",
    )
    list_filter = ("timestamp", "created_at", "rule", "acknowledged")
    search_fields = ("rule__name",)
    readonly_fields = ("id", "timestamp", "created_at", "related_telemetry")
    date_hierarchy = "timestamp"
    actions = ["mark_acknowledged", "mark_unacknowledged"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "rule__device_metric__device"
        )

    @admin.display(description="Device")
    def rule_device(self, obj):
        return obj.rule.device_metric.device.name

    @admin.display(description="Related Rule")
    def related_telemetry(self, obj):
        if not obj.pk:
            return format_html('<span style="color: gray;">{}</span>', 'No rule')
        dm = obj.rule.device_metric
        list_url = (
            reverse("admin:devices_telemetry_changelist") + f"?device_metric__id={dm.id}"
        )
        recent = (
            Telemetry.objects.filter(device_metric=dm)
            .order_by("-ts")[:10]
        )
        lines = [format_html('<a href="{}">View all telemetry for this metric</a>', list_url)]
        for t in recent:
            change_url = reverse("admin:devices_telemetry_change", args=[t.pk])
            lines.append(
                format_html(
                    '<div><a href="{}">{} — {}</a></div>',
                    change_url,
                    t.ts,
                    t.formatted_value_with_type(),
                )
            )
        return format_html("{}", mark_safe("".join(lines)))


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
