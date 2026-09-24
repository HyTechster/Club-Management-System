from django.urls import path

from . import views

urlpatterns = [
    path("committee/", views.committee_list, name="committee"),
]
