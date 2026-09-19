from django.urls import path

from core.views import ApiRootView, CapabilitiesView, HealthView


urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    path("health/", HealthView.as_view(), name="health"),
    path("capabilities/", CapabilitiesView.as_view(), name="capabilities"),
]
