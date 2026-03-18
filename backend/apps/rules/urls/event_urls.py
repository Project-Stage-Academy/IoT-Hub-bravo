from django.urls import path

from apps.rules.views.event_views import (
    list_events,
    event_detail,
    ack_event,
    receive_external_event
)

urlpatterns = [
    path("", list_events, name="events-list"),
    path("<uuid:event_uuid>/", event_detail, name="events-detail"),
    path("<uuid:event_uuid>/ack/", ack_event, name="events-ack"),
    path("external/", receive_external_event, name='external-events'),
]
