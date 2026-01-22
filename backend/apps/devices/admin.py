from django.contrib import admin
from django.utils.html import format_html
from .models import Device, Telemetry, Metric, DeviceMetric
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
    readonly_fields = (
        "id",
        "created_at",
        "latest_telemetry_timestamp",
        "recent_telemetry_display",
    )
    date_hierarchy = "created_at"
    actions = ["enable_devices", "disable_devices"]
    fieldsets = (
        (
            "Device Information",
            {
                "fields": (
                    "id",
                    "serial_id",
                    "name",
                    "description",
                    "user",
                    "is_active",
                    "created_at",
                )
            },
        ),
        (
            "Telemetry Data",
            {
                "fields": ("latest_telemetry_timestamp", "recent_telemetry_display"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Latest Telemetry")
    def latest_telemetry_timestamp(self, obj):
        from django.db.models import Max

        latest = Telemetry.objects.filter(device_metric__device=obj).aggregate(
            Max("ts")
        )["ts__max"]
        if latest:
            return latest
        return format_html('<span style="color: gray;">No data</span>')

    @admin.display(description="Recent Telemetry (Last 10)")
    def recent_telemetry_display(self, obj):
        telemetries = (
            Telemetry.objects.filter(device_metric__device=obj)
            .select_related("device_metric__metric")
            .order_by("-ts")[:10]
        )

        if not telemetries:
            return format_html(
                '<p style="color: gray;">No telemetry data available</p>'
            )

        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f2f2f2;"><th style="border: 1px solid #ddd; padding: 8px;">Metric</th><th style="border: 1px solid #ddd; padding: 8px;">Value</th><th style="border: 1px solid #ddd; padding: 8px;">Timestamp</th></tr>'

        for t in telemetries:
            value = ""
            if t.value_numeric is not None:
                value = f"{t.value_numeric:.3f}"
            elif t.value_bool is not None:
                value = str(t.value_bool)
            elif t.value_str is not None:
                value = t.value_str

            html += f'<tr><td style="border: 1px solid #ddd; padding: 8px;">{t.device_metric.metric.metric_type}</td><td style="border: 1px solid #ddd; padding: 8px;">{value}</td><td style="border: 1px solid #ddd; padding: 8px;">{t.ts}</td></tr>'

        html += "</table>"
        return format_html(html)

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


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ("id", "metric_type", "data_type")
    list_filter = ("data_type",)
    search_fields = ("metric_type",)
    readonly_fields = ("id",)


@admin.register(DeviceMetric)
class DeviceMetricAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "metric", "device_active")

    @admin.display(boolean=True, description="Device Active")
    def device_active(self, obj):
        return obj.device.is_active
