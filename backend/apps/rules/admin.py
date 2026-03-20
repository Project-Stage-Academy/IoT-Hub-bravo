import json
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from django.utils.timezone import localtime
from .models import Rule, Event, EventDelivery
from .validators.rule_validator import validate_action, validate_condition


class RuleAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if self.user and not self.user.is_superuser:
            self.fields["device_metric"].queryset = self.fields["device_metric"].queryset.filter(
                device__user=self.user
            )

    class Meta:
        model = Rule
        fields = "__all__"
        help_texts = {
            "name": "A short, unique name for this rule (e.g. 'CPU Overheat Alert').",
            "description": "Optional. Describe what this rule monitors and why.",
            "device_metric": "The specific device+metric pair this rule applies to.",
            "is_active": "Inactive rules are stored but never evaluated.",
            "condition": "Expression or criteria that trigger this rule.",
            "action": "What happens when this rule triggers.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "condition": forms.Textarea(attrs={"rows": 5}),
            "action": forms.Textarea(attrs={"rows": 5}),
        }

    def clean(self):
        cleaned = super().clean()

        device_metric = cleaned.get("device_metric")
        is_active = cleaned.get("is_active")
        if is_active and device_metric is None:
            raise ValidationError("Cannot activate a rule without a device metric assigned.")
        return cleaned

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise ValidationError("Rule name cannot be blank or whitespace only.")

        device_metric = self.cleaned_data.get("device_metric")
        if device_metric:
            qs = Rule.objects.filter(name__iexact=name, device_metric=device_metric)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    f'A rule named "{name}" already exists for this device metric.'
                )

        return name

    def clean_condition(self):
        raw = self.cleaned_data.get("condition")
        validate_condition(raw)
        if isinstance(raw, str):
            return json.loads(raw)
        return raw

    def clean_action(self):
        raw = self.cleaned_data.get("action")
        validate_action(raw)
        if isinstance(raw, str):
            return json.loads(raw)
        return raw


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    form = RuleAdminForm

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)

        class FormWithUser(Form):
            def __init__(self_inner, *args, **inner_kwargs):
                inner_kwargs.setdefault("user", request.user)
                Form.__init__(self_inner, *args, **inner_kwargs)

        return FormWithUser

    list_display = (
        "id",
        "name",
        "device_metric",
        "rule_status",
        "last_triggered_display",
        "condition",
        "action",
    )
    list_filter = ("is_active", "device_metric")
    search_fields = (
        "name",
        "description",
        "device_metric__device__name",
        "device_metric__metric__metric_type",
    )
    search_help_text = "Search by rule name, description, device name, or metric type."
    ordering = ("-id",)
    list_per_page = 25

    readonly_fields = ("id", "last_triggered_display")
    save_on_top = True  # save buttons at top and bottom of form

    fieldsets = (
        (
            "Identity",
            {"fields": ("id", "name", "description")},
        ),
        (
            "Configuration",
            {
                "fields": ("device_metric", "condition", "action"),
                "description": "Link this rule to a device metric and define its condition and action.",
            },
        ),
        (
            "Status",
            {
                "fields": ("is_active", "last_triggered_display"),
                "classes": ("collapse",),
                "description": "Runtime state of this rule. 'Last triggered' is read-only.",
            },
        ),
    )

    def has_add_permission(self, request):
        return request.user.is_staff or request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return request.user.is_staff

        return request.user.is_staff and obj.device_metric.device.user == request.user

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return request.user.is_staff

        return request.user.is_staff and obj.device_metric.device.user == request.user

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return request.user.is_staff

        return request.user.is_staff and obj.device_metric.device.user == request.user

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        return qs.filter(device_metric__device__user=request.user)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = "updated" if change else "created"
        status = "active" if obj.is_active else "inactive"
        self.message_user(
            request,
            f'Rule "{obj.name}" was {action} and is currently {status}.',
            messages.SUCCESS,
        )

    def delete_model(self, request, obj):
        name = obj.name
        super().delete_model(request, obj)
        self.message_user(
            request,
            f'Rule "{name}" and all its associated events have been deleted.',
            messages.WARNING,
        )

    @admin.display(description="Active", boolean=True, ordering="is_active")
    def rule_status(self, obj):
        return obj.is_active

    @admin.display(description="Last Triggered")
    def last_triggered_display(self, obj):
        from django.db.models import Max

        latest = Event.objects.filter(rule=obj.id).aggregate(Max("rule_triggered_at"))[
            "rule_triggered_at__max"
        ]
        if latest:
            local = localtime(latest)
            return format_html(
                '<span title="{}">{}</span>',
                local.isoformat(),
                local.strftime("%Y-%m-%d %H:%M"),
            )
        return format_html('<span style="color: gray;">Never</span>')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_select_related = ()

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
        "rule",
        "trigger_device_serial_id",
    )
    readonly_fields = ("id", "event_uuid", "rule_triggered_at", "created_at", "trigger_context")
    date_hierarchy = "rule_triggered_at"
    ordering = ("-rule_triggered_at",)
    actions = ["mark_acknowledged", "mark_unacknowledged"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        rule_ids = set(qs.values_list("rule", flat=True))
        rules_map = {r.id: r for r in Rule.objects.filter(id__in=rule_ids)}

        for obj in qs:
            obj._rule_obj = rules_map.get(obj.rule)

        return qs

    @admin.display(description="Device Serial ID", ordering="trigger_device_serial_id")
    def device_link(self, obj):
        if obj.trigger_device_serial_id:
            url = f"{reverse('admin:devices_device_changelist')}?q={obj.trigger_device_serial_id}"
            return format_html('<a href="{}">{}</a>', url, obj.trigger_device_serial_id)
        return "-"

    @admin.display(description="Rule")
    def rule_link(self, obj):
        rule = getattr(obj, "_rule_obj", None)

        if rule:
            url = reverse("admin:rules_rule_change", args=[rule.id])
            return format_html('<a href="{}">{}</a>', url, rule.name)

        if obj.rule:
            return f"Rule #{obj.rule} (not found)"

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
