from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect,render
from accounts.models import Profile

@login_required
def post_login_redirect(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    role = profile.role

    if role == "ADMIN":
        return redirect("admin:index")
    elif role == "DOCTOR":
        return redirect("doctors:doctor_dashboard")
    elif role == "STAFF":
        return redirect("staff:staff_dashboard")
    else:
        return redirect("services")
@login_required
def home(request):
    return render(request, "home.html")