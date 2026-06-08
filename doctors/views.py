from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from appointments.models import Appointment, AppointmentReport

def doctor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not (
            request.user.is_authenticated and
            hasattr(request.user, "profile") and
            request.user.profile.role == "DOCTOR"
        ):
            return redirect("/auth/register/")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import date, datetime
from django.contrib import messages

from appointments.models import Appointment, TimeSlot
from .models import Doctor
from functools import wraps


@login_required
@doctor_required
def doctor_dashboard(request):
    return render(request, "doctors/dashboard.html")

@login_required
@doctor_required
def doctor_appointments(request):
    doctor = get_object_or_404(Doctor, user=request.user)

    date_str = request.GET.get("date")
    selected_date = (
        datetime.strptime(date_str, "%Y-%m-%d").date()
        if date_str else date.today()
    )

    appointments = Appointment.objects.filter(
        doctor=doctor,
        slot__date=selected_date
    ).select_related(
        "user", "booked_by_staff", "slot"
    ).order_by("slot__start_time")

    return render(
        request,
        "doctors/doctor_appointments.html",
        {
            "appointments": appointments,
            "selected_date": selected_date,
            "today": date.today(),
        }
    )


@login_required
@doctor_required
def doctor_edit_slot(request, slot_id):
    slot = get_object_or_404(
        TimeSlot,
        id=slot_id,
        doctor__user=request.user,
        is_available=True,
        date__gte=timezone.now().date()
    )

    if request.method == "POST":
        slot.start_time = datetime.strptime(
            request.POST.get("start_time"), "%H:%M"
        ).time()
        slot.end_time = datetime.strptime(
            request.POST.get("end_time"), "%H:%M"
        ).time()
        slot.save()

    return redirect("doctors:doctor_slots")


@login_required
@doctor_required
def doctor_mark_completed(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        doctor__user=request.user
    )

    if request.method == "POST":
        if request.POST.get("cancel"):
            appointment.status = "CANCELLED"
        else:
            appointment.status = "COMPLETED"
        appointment.save()

    return redirect("doctors:doctor_appointments")

@login_required
@doctor_required
def delete_slot(request, slot_id):
    if request.method != "POST":
        return redirect("doctors:doctor_slots")

    slot = get_object_or_404(
        TimeSlot,
        id=slot_id,
        doctor__user=request.user,
        is_available=True,
        date__gte=timezone.localdate()
    )

    date_str = slot.date.strftime("%Y-%m-%d")
    slot.delete()
    messages.success(request, "Slot deleted")
    return redirect(f"/dashboard/doctor/slots/?date={date_str}")


@login_required
def doctor_list(request):
    profile = getattr(request.user, "profile", None)

    if not profile or profile.role != "USER":
        return redirect("post_login_redirect")


    doctors = Doctor.objects.filter(is_active=True)
    consultation_type = request.GET.get("type", "ONLINE")

    return render(
        request,
        "doctors/doctor_list.html",
        {
            "doctors": doctors,
            "consultation_type": consultation_type
        }
    )

@login_required
@doctor_required
def doctor_slots(request):
    doctor = get_object_or_404(Doctor, user=request.user)

    # selected date (default = today)
    date_str = request.GET.get("date")
    selected_date = (
        datetime.strptime(date_str, "%Y-%m-%d").date()
        if date_str else timezone.localdate()
    )

    # prevent past date selection
    if selected_date < timezone.localdate():
        messages.error(request, "Cannot manage past slots")
        return redirect("doctors:doctor_slots")

    # fetch slots for date
    slots = TimeSlot.objects.filter(
        doctor=doctor,
        date=selected_date
    ).order_by("start_time")

    # ADD SLOT
    if request.method == "POST":
        try:
            start_time = datetime.strptime(
                request.POST.get("start_time"), "%H:%M"
            ).time()
            end_time = datetime.strptime(
                request.POST.get("end_time"), "%H:%M"
            ).time()

            slot = TimeSlot(
                doctor=doctor,
                date=selected_date,
                start_time=start_time,
                end_time=end_time
            )
            slot.full_clean()
            slot.save()
            messages.success(request, "Slot added successfully")
            return redirect(f"?date={selected_date}")

        except Exception as e:
            messages.error(request, str(e))

    return render(
        request,
        "doctors/slots.html",
        {
            "slots": slots,
            "selected_date": selected_date,
            "today": timezone.localdate(),
        }
    )



@login_required
@doctor_required
def doctor_view_reports(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        doctor__user=request.user
    )

    reports = appointment.reports.all()  # ✅ related_name works

    return render(
        request,
        "doctors/doctor_view_reports.html",
        {
            "appointment": appointment,
            "reports": reports
        }
    )

