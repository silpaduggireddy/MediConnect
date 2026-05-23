from django.urls import path
from core.views import post_login_redirect
from django.contrib.auth.views import LogoutView
from .views import phone_register, otp_verify, login_view, check_user

urlpatterns = [
    path("register/", phone_register, name="phone_register"),
    path("verify-otp/", otp_verify, name="otp_verify"),
    path("login/", login_view, name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("post-login/", post_login_redirect, name="post_login_redirect"),
    path("check-user/", check_user, name="check_user"),
]
