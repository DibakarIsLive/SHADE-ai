from django.urls import path

from events.views import EventListCreateView


urlpatterns = [
    path("", EventListCreateView.as_view(), name="event-list-create"),
]
