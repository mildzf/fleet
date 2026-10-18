
from django.contrib.auth import views as auth_views
from django.urls import path

from .views import MandatoryPasswordChangeView

app_name = "accounts"

urlpatterns = [
    path(
        "password/change/",
        MandatoryPasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
]

