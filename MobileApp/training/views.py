from django.shortcuts import render
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import TrainingCourse
from django.utils import timezone
from .models import TrainingEnrollment
from .models import TrainingCourse, TrainingEnrollment

def training_list(request):
    courses = TrainingCourse.objects.filter(
        status__in=["UPCOMING", "ONGOING"]
    )

    enrolled_course_ids = []

    if request.user.is_authenticated:
        enrolled_course_ids = list(
            TrainingEnrollment.objects.filter(
                user=request.user
            ).values_list("course_id", flat=True)
        )

    return render(
        request,
        "training/training_list.html",
        {
            "courses": courses,
            "enrolled_course_ids": enrolled_course_ids,
        }
    )


@login_required
def course_enroll(request, course_id):
    course = get_object_or_404(
        TrainingCourse,
        id=course_id,
        is_active=True   # ✅ SAFETY FILTER
    )

    # Later: enrollment logic
    return redirect("training_list")


@login_required
def course_enroll(request, course_id):
    course = get_object_or_404(
        TrainingCourse,
        id=course_id,
        status__in=["UPCOMING", "ONGOING"]
    )

    # prevent double enrollment
    if TrainingEnrollment.objects.filter(
        course=course,
        user=request.user
    ).exists():
        return redirect("training:training_list")

    if request.method == "POST":
        TrainingEnrollment.objects.create(
            course=course,
            user=request.user,
            full_name=request.POST["full_name"],
            phone=request.POST["phone"],
            email=request.POST["email"],
        )
        return redirect("training:training_list")

    return render(
        request,
        "training/course_enroll.html",
        {"course": course}
    )


@login_required
def my_trainings(request):
    enrollments = TrainingEnrollment.objects.select_related("course").filter(
        user=request.user
    ).order_by("-enrolled_at")

    return render(
        request,
        "training/my_trainings.html",
        {
            "enrollments": enrollments
        }
    )
