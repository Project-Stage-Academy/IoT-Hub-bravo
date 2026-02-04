from django.urls import path
from apps.devices.views import DeviceView, DeviceDetailView


urlpatterns = [
    path("", DeviceView.as_view(), name="device-list-create"),
    path("<int:pk>/", DeviceDetailView.as_view(), name="device-detail"),
]
