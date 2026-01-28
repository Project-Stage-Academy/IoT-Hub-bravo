from django.contrib import admin
from django.utils.html import format_html
from .models import Rule, Event


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "device_metric", "rule_status", "last_triggered")
    list_filter = ("is_active", "device_metric")
    search_fields = (
        "name",
        "description",
        "device_metric__device__name",
        "device_metric__metric__name",
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
        return format_html('<span style="color: gray;">Never</span>')


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
    readonly_fields = ("id", "timestamp", "created_at")
    date_hierarchy = "timestamp"
    actions = ["mark_acknowledged", "mark_unacknowledged"]

    @admin.display(description="Device")
    def rule_device(self, obj):
        return obj.rule.device_metric.device.name

    @admin.action(description="Mark selected events as acknowledged")
    def mark_acknowledged(self, request, queryset):
        updated = queryset.update(acknowledged=True)
        self.message_user(request, f"{updated} event(s) marked as acknowledged.")

    @admin.action(description="Mark selected events as unacknowledged")
    def mark_unacknowledged(self, request, queryset):
        updated = queryset.update(acknowledged=False)
        self.message_user(request, f"{updated} event(s) marked as unacknowledged.")
