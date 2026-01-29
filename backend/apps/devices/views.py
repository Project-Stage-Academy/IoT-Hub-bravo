from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Device
from .serializers.device_serializer import DeviceSerializer
from .serializers.auth_serializator import CustomTokenObtainPairSerializer
from apps.users.models import User 
from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class DeviceViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Device.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save()
