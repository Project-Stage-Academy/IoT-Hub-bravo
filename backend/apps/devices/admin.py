import csv

from django.contrib import admin
from django.db.models import Max
from django.http import HttpResponse
from django.utils.html import format_html, format_html_join

from .models import Device, Telemetry, Metric, DeviceMetric


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

    def get_queryset(self, request):
        """
        Annotate latest telemetry timestamp to avoid N+1 queries on the changelist.
        """
        qs = super().get_queryset(request)
        # Reverse relations (default related_name):
        # Device -> DeviceMetric: devicemetric_set (query name: devicemetric)
        # DeviceMetric -> Telemetry: telemetry_set (query name: telemetry)
        return qs.annotate(_latest_ts=Max("devicemetric__telemetry__ts"))

    @admin.display(description="Latest Telemetry")
    def latest_telemetry_timestamp(self, obj):
        latest = getattr(obj, "_latest_ts", None)
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
            return format_html('<p style="color: gray;">No telemetry data available</p>')

        header = format_html(
            "<tr style='background-color:#f2f2f2;'>"
            "<th style='border:1px solid #ddd; padding:8px;'>Metric</th>"
            "<th style='border:1px solid #ddd; padding:8px;'>Value</th>"
            "<th style='border:1px solid #ddd; padding:8px;'>Timestamp</th>"
            "</tr>"
        )

        rows = format_html_join(
            "",
            "<tr>"
            "<td style='border:1px solid #ddd; padding:8px;'>{}</td>"
            "<td style='border:1px solid #ddd; padding:8px;'>{}</td>"
            "<td style='border:1px solid #ddd; padding:8px;'>{}</td>"
            "</tr>",
            (
                (
                    t.device_metric.metric.metric_type,
                    t.formatted_value(),
                    t.ts,
                )
                for t in telemetries
            ),
        )

        return format_html(
            "<table style='width:100%; border-collapse:collapse;'>{}{}</table>",
            header,
            rows,
        )

    @admin.action(description="Enable selected devices")
    def enable_devices(self, request, queryset):
        if not request.user.has_perm("devices.change_device"):
            self.message_user(request, "Permission denied.", level="error")
            return

        try:
            updated = queryset.update(is_active=True)
        except Exception as exc:
            self.message_user(request, f"Failed to enable devices: {exc}", level="error")
            return

        self.message_user(request, f"{updated} device(s) successfully enabled.")

    @admin.action(description="Disable selected devices")
    def disable_devices(self, request, queryset):
        if not request.user.has_perm("devices.change_device"):
            self.message_user(request, "Permission denied.", level="error")
            return

        try:
            updated = queryset.update(is_active=False)
        except Exception as exc:
            self.message_user(request, f"Failed to disable devices: {exc}", level="error")
            return

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
        value = obj.formatted_value_with_type()
        if value:
            return value
        return format_html('<span style="color: gray;">N/A</span>')

    @admin.action(description="Export selected telemetry to CSV")
    def export_to_csv(self, request, queryset):
        # Optional, but reasonable: exporting implies viewing permission.
        if not request.user.has_perm("devices.view_telemetry"):
            self.message_user(request, "Permission denied.", level="error")
            return None

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="telemetry_export.csv"'

        writer = csv.writer(response)
        writer.writerow(["ID", "Device", "Metric", "Value", "Timestamp", "Created At"])

        qs = queryset.select_related("device_metric__device", "device_metric__metric")
        for telemetry in qs:
            writer.writerow(
                [
                    telemetry.id,
                    telemetry.device_metric.device.name,
                    telemetry.device_metric.metric.metric_type,
                    telemetry.formatted_value(),
                    telemetry.ts,
                    telemetry.created_at,
                ]
            )

        self.message_user(request, f"{queryset.count()} telemetry record(s) exported to CSV.")
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
