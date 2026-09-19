from django.urls import path

from monitoring.views import MonitoringStartView, MonitoringStatusView, MonitoringStopView


urlpatterns = [
    path("status/", MonitoringStatusView.as_view(), name="monitoring-status"),
    path("start/", MonitoringStartView.as_view(), name="monitoring-start"),
    path("stop/", MonitoringStopView.as_view(), name="monitoring-stop"),
]
