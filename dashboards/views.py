from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect,get_object_or_404
from django.utils.timezone import now,localdate
from django.contrib import messages
from doctors.models import Doctor
from appointments.models import Appointment, TimeSlot
from django.db.models import Q
from datetime import date, datetime


@login_required
def dashboard_redirect(request):
    user = request.user

    # Admin
    if user.is_superuser:
        return redirect("/admin/")

    # Doctor
    if Doctor.objects.filter(user=user).exists():
        return redirect("doctor_dashboard")

    # Staff (we will wire later)
    if hasattr(user, "profile") and user.profile.role == "STAFF":
        return redirect("staff_dashboard")

    # Default → Patient
    return redirect("patient_dashboard")


# --------------------
# PATIENT DASHBOARD
# --------------------
@login_required
def patient_dashboard(request):
    return render(request, "dashboards/patient_dashboard.html")


# --------------------
# DOCTOR DASHBOARD (MAIN)
# --------------------
@login_required
def doctor_dashboard(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect("phone_register")

    today = now().date()

    today_appointments_count = Appointment.objects.filter(
        doctor=doctor,
        slot__date=today
    ).count()

    context = {
        "doctor": doctor,
        "today_appointments_count": today_appointments_count
    }

    return render(
        request,
        "dashboards/doctor_dashboard.html",
        context
    )


# --------------------
# STAFF DASHBOARD
# --------------------
@login_required
def staff_dashboard(request):
    return render(request, "dashboards/staff_dashboard.html")


# --------------------
# DOCTOR DAILY APPOINTMENTS
# --------------------
@login_required
def doctor_daily_appointments(request):
    try:
        doctor = Doctor.objects.get(user=request.user)
    except Doctor.DoesNotExist:
        return redirect("phone_register")

    today = now().date()

    appointments = Appointment.objects.filter(
        doctor=doctor,
        slot__date=today
    ).select_related("user", "slot").order_by("slot__start_time")

    context = {
        "doctor": doctor,
        "appointments": appointments,
        "today": today,
    }

    return render(
        request,
        "dashboards/doctor_daily_appointments.html",
        context
    )

@login_required
def doctor_slots(request):
    return render(request, "dashboards/doctor_slots.html")

@login_required
def doctor_slots(request):
    doctor = Doctor.objects.get(user=request.user)

    if request.method == "POST":
        date = request.POST["date"]
        start_time = request.POST["start_time"]
        end_time = request.POST["end_time"]

        # 🔴 Prevent overlapping slots
        overlap = TimeSlot.objects.filter(
            doctor=doctor,
            date=date
        ).filter(
            Q(start_time__lt=end_time) &
            Q(end_time__gt=start_time)
        ).exists()

        if overlap:
            messages.error(request, "Slot overlaps with existing slot")
        else:
            TimeSlot.objects.create(
                doctor=doctor,
                date=date,
                start_time=start_time,
                end_time=end_time
            )
            messages.success(request, "Slot added successfully")

        return redirect("doctor_slots")

    slots = TimeSlot.objects.filter(
        doctor=doctor
    ).order_by("date", "start_time")

    return render(
        request,
        "dashboards/doctor_slots.html",
        {"slots": slots}
    )


@login_required
def delete_slot(request, slot_id):
    doctor = Doctor.objects.get(user=request.user)

    slot = TimeSlot.objects.filter(
        id=slot_id,
        doctor=doctor
    ).first()

    if not slot:
        messages.error(request, "Slot not found")
        return redirect("doctor_slots")

    # 🔴 Prevent deleting booked slots
    if not slot.is_available:
        messages.error(request, "Cannot delete a booked slot")
        return redirect("doctor_slots")

    slot.delete()
    messages.success(request, "Slot deleted successfully")
    return redirect("doctor_slots")


from django.contrib.auth.decorators import login_required
from django.utils.timezone import localdate
from appointments.models import Appointment

@login_required
def doctor_appointments(request):
    doctor = request.user.doctor

    selected_date_str = request.GET.get("date")

    if selected_date_str:
        selected_date = datetime.strptime(
            selected_date_str, "%Y-%m-%d"
        ).date()
    else:
        selected_date = localdate()

    appointments = Appointment.objects.filter(
        doctor=doctor,
        slot__date=selected_date
    ).select_related("user", "slot").order_by("slot__start_time")

    return render(
        request,
        "doctors/doctor_appointments.html",
        {
            "appointments": appointments,
            "doctor": doctor,
            "selected_date": selected_date,
            "today": localdate(),
        }
    )

@login_required
def doctor_appointment_history(request, appointment_id):
    doctor = request.user.doctor

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        doctor=doctor
    )

    return render(
        request,
        "dashboards/doctor_appointment_history.html",
        {
            "appointment": appointment,
            "reports": appointment.reports.all()
        }
    )

# dashboards/views.py

@login_required
def staff_appointments(request):
    appointments = Appointment.objects.select_related(
        "doctor", "user", "slot"
    ).order_by("-slot__date")

    return render(
        request,
        "staff/staff_appointments.html",
        {"appointments": appointments}
    )
