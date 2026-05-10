from django.urls import path
from .views import home, post_login_redirect
from django.shortcuts import redirect

def entry_point(request):
    if request.user.is_authenticated:
        return redirect("/post-login/")
    return redirect("phone_register")

urlpatterns = [
    #path("", home, name="home"),
    path("", entry_point, name="entry_point"),
    path("post-login/", post_login_redirect, name="post-login"),

]

