from django.urls import path
from core.views import post_login_redirect
from .views import phone_register, otp_verify
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path("register/", phone_register, name="phone_register"),
    path("verify-otp/", otp_verify, name="otp_verify"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("post-login/", post_login_redirect, name="post_login_redirect"),
]
