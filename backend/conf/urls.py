'''
URL configuration for conf project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
'''
from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
from apps.users.views import login

from apps.devices.views import ingest_telemetry

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/telemetry/', ingest_telemetry, name="ingest-telemetry"),
    path("api/auth/login/", login, name="user-auth"),
    path("api/devices/", include("apps.devices.urls.device_urls")),
    path("api/telemetry/", include("apps.devices.urls.telemetry_urls")),
    path("api/events/", include("apps.rules.urls.event_urls")),
    path('prometheus/', include('django_prometheus.urls')),  # access metrics at "prometheus/metrics/"
    path('api/rules/', include('apps.rules.urls.rule_urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
