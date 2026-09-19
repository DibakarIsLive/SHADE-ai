"""HTTP URL configuration for SHADE-ai."""

from django.urls import include, path


urlpatterns = [
    path("api/", include("core.urls")),
    path("api/cameras/", include("cameras.urls")),
    path("api/events/", include("events.urls")),
    path("api/monitoring/", include("monitoring.urls")),
]
