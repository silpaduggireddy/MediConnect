from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import TrainingCourse


@login_required
def service_selection(request):

    return render(request, "services/service_selection.html")


@login_required
def online_consultation(request):

    # reuse your existing booking flow
    return redirect("doctors:doctor_list")


@login_required
def clinic_consultation(request):

    return redirect("appointments:book_appointment")


@login_required
def training_list(request):
    courses = TrainingCourse.objects.filter(is_active=True)
    return render(request, "services/training_list.html", {
        "courses": courses
    })
