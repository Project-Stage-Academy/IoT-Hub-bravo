from django.contrib import admin
from django.utils.html import format_html
from .models import Rule, Event, EventDelivery
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

        latest = Event.objects.filter(rule=obj).aggregate(Max("rule_triggered_at"))[
            "rule_triggered_at__max"
        ]
        if latest:
            return latest
        return format_html('<span style="color: gray;">{}</span>', 'Never')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_select_related = ("rule__device_metric__device",)

    list_display = (
        "id",
        "event_uuid",
        "rule_link",
        "acknowledged",
        "rule_triggered_at",
        "created_at",
        "device_link",
        "trigger_context_summary",
    )

    list_filter = ("rule_triggered_at", "created_at", "rule", "acknowledged")
    search_fields = (
        "event_uuid",
        "rule__name",
        "rule__device_metric__device__name",
        "trigger_device_serial_id",
    )
    readonly_fields = ("id", "event_uuid", "rule_triggered_at", "created_at", "trigger_context")
    date_hierarchy = "rule_triggered_at"
    ordering = ("-rule_triggered_at",)
    actions = ["mark_acknowledged", "mark_unacknowledged"]

    @admin.display(description="Device Serial ID", ordering="trigger_device_serial_id")
    def device_link(self, obj):
        if obj.trigger_device_serial_id:
            url = f"{reverse('admin:devices_device_changelist')}?q={obj.trigger_device_serial_id}"
            return format_html('<a href="{}">{}</a>', url, obj.trigger_device_serial_id)
        return "-"

    @admin.display(description="Rule", ordering="rule__name")
    def rule_link(self, obj):
        if obj.rule:
            url = reverse("admin:rules_rule_change", args=[obj.rule.id])
            return format_html('<a href="{}">{}</a>', url, obj.rule.name)
        return "-"

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

    @admin.display(description="Trigger Context Summary")
    def trigger_context_summary(self, obj):
        if obj.trigger_context:
            return format_html(
                '<pre style="white-space: pre-wrap; max-width: 400px;">{}</pre>',
                str(obj.trigger_context),
            )
        return "-"


@admin.register(EventDelivery)
class EventDeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "event_link",
        "delivery_type",
        "status_colored",
        "attempts",
        "response_status",
        "next_retry_at",
        "updated_at",
    )

    list_filter = ("status", "delivery_type", "created_at")

    search_fields = (
        "event_uuid",
        "trigger_device_serial_id",
        "rule_id",
    )

    readonly_fields = (
        "event_uuid",
        "rule_id",
        "trigger_device_serial_id",
        "delivery_type",
        "payload",
        "status",
        "attempts",
        "max_attempts",
        "last_attempt_at",
        "next_retry_at",
        "response_status",
        "error_message",
        "created_at",
        "updated_at",
    )

    exclude = ("payload",)

    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    @admin.display(description="Event UUID", ordering="event_uuid")
    def event_link(self, obj):
        """Makes the Event UUID clickable, linking to the Event changelist filtered by this UUID."""
        if obj.event_uuid:
            url = f"{reverse('admin:rules_event_changelist')}?q={obj.event_uuid}"
            short_uuid = str(obj.event_uuid).split('-')[0]
            return format_html(
                '<a href="{}" title="{}">{}...</a>', url, obj.event_uuid, short_uuid
            )
        return "-"

    @admin.display(description="Status", ordering="status")
    def status_colored(self, obj):
        """Colors for different statuses to enhance visibility in the admin list view."""
        colors = {
            "pending": "orange",
            "processing": "blue",
            "retry": "purple",
            "success": "green",
            "rejected": "red",
        }
        color = colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display().upper(),
        )
