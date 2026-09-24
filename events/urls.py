from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    path("", views.EventListView.as_view(), name="list"),
    path("events/<int:pk>/", views.EventDetailView.as_view(), name="detail"),
    path("events/<int:pk>/qr/", views.qr_display, name="qr"),
    path("checkin/<str:token>/", views.checkin, name="checkin"),
]
