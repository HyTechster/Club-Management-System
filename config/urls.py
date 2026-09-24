from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from accounts.views import profile

admin.site.site_header = "Club Back-Office"
admin.site.site_title = "Club Back-Office"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("me/", profile, name="profile"),
    path("accounts/", include("accounts.urls")),
    path("accounts/login/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("committee.urls")),
    path("", include("events.urls")),
]
