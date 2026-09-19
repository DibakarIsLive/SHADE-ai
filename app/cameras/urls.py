from django.urls import path

from cameras.views import CameraListCreateView


urlpatterns = [
    path("", CameraListCreateView.as_view(), name="camera-list-create"),
]
