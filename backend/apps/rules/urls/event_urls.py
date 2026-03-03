from django.urls import path

from apps.rules.views.event_views import (
    list_events,
    event_detail,
    ack_event,
)

urlpatterns = [
    path("", list_events, name="events-list"),
    path("<int:event_id>/", event_detail, name="events-detail"),
    path("<int:event_id>/ack/", ack_event, name="events-ack"),
]
