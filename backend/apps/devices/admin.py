from django.contrib import admin
from django.utils.html import format_html
from .models import Device, Telemetry
import csv
from django.http import HttpResponse


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "serial_id",
        "name",
        "user",
        "is_active",
        "latest_telemetry_timestamp",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("serial_id", "name", "user__username", "description")
    readonly_fields = ("id", "created_at", "latest_telemetry_timestamp")
    date_hierarchy = "created_at"
    actions = ["enable_devices", "disable_devices"]

    @admin.display(description="Latest Telemetry")
    def latest_telemetry_timestamp(self, obj):
        from django.db.models import Max

        latest = Telemetry.objects.filter(device_metric__device=obj).aggregate(
            Max("ts")
        )["ts__max"]
        if latest:
            return latest
        return format_html('<span style="color: gray;">No data</span>')

    @admin.action(description="Enable selected devices")
    def enable_devices(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} device(s) successfully enabled.")

    @admin.action(description="Disable selected devices")
    def disable_devices(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} device(s) successfully disabled.")


@admin.register(Telemetry)
class TelemetryAdmin(admin.ModelAdmin):
    list_display = ("id", "device_metric", "display_value", "ts", "created_at")
    list_filter = ("ts", "created_at", "device_metric")
    search_fields = ("device_metric__device__name", "device_metric__metric__name")
    readonly_fields = ("id", "value_numeric", "value_bool", "value_str", "created_at")
    date_hierarchy = "ts"
    actions = ["export_to_csv"]

    @admin.display(description="Value")
    def display_value(self, obj):
        if obj.value_numeric is not None:
            return f"{obj.value_numeric:.3f} (numeric)"
        elif obj.value_bool is not None:
            return f"{obj.value_bool} (bool)"
        elif obj.value_str is not None:
            return f"{obj.value_str} (str)"
        return format_html('<span style="color: gray;">N/A</span>')

    @admin.action(description="Export selected telemetry to CSV")
    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="telemetry_export.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Device", "Metric", "Value", "Timestamp", "Created At"])

        for telemetry in queryset:
            value = ""
            if telemetry.value_numeric is not None:
                value = f"{telemetry.value_numeric:.3f}"
            elif telemetry.value_bool is not None:
                value = str(telemetry.value_bool)
            elif telemetry.value_str is not None:
                value = telemetry.value_str

            writer.writerow(
                [
                    telemetry.id,
                    telemetry.device_metric.device.name,
                    telemetry.device_metric.metric.metric_type,
                    value,
                    telemetry.ts,
                    telemetry.created_at,
                ]
            )

        self.message_user(
            request, f"{queryset.count()} telemetry record(s) exported to CSV."
        )
        return response
