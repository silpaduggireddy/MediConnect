from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.db import transaction
from datetime import timedelta, datetime, time, date

from .models import TimeSlot, Appointment, AppointmentReport
from doctors.models import Doctor


# ------------------------
# HOLIDAYS
# ------------------------
HOLIDAYS = [
    date(2025, 1, 26),
    date(2025, 8, 15),
    date(2025, 10, 2),
]


# ------------------------
# SLOT GENERATION
# ------------------------
def generate_default_slots(doctor, slot_date):
    # ❌ No past dates
    if slot_date < timezone.localdate():
        return

    # ❌ No weekends or holidays
    if slot_date.weekday() >= 5 or slot_date in HOLIDAYS:
        return
    working_hours = [
        (time(10, 0), time(12, 0)),
        (time(13, 0), time(17, 0)),
    ]

    for start, end in working_hours:
        current = datetime.combine(slot_date, start)
        end_dt = datetime.combine(slot_date, end)

        while current < end_dt:
            TimeSlot.objects.get_or_create(
                doctor=doctor,
                date=slot_date,
                start_time=current.time(),
                end_time=(current + timedelta(minutes=30)).time(),
                defaults={"is_available": True}
            )
            current += timedelta(minutes=30)


# ------------------------
# AJAX: AVAILABLE SLOTS
# ------------------------
@login_required
def available_slots_by_date(request, doctor_id):
    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse({"slots": []})

    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({"slots": []})

    if selected_date.weekday() >= 5 or selected_date in HOLIDAYS:
        return JsonResponse({"slots": []})

    doctor = get_object_or_404(Doctor, id=doctor_id)

    if not TimeSlot.objects.filter(doctor=doctor, date=selected_date).exists():
        generate_default_slots(doctor, selected_date)

    slots = TimeSlot.objects.filter(
        doctor=doctor,
        date=selected_date,
        is_available=True
    ).order_by("start_time")

    return JsonResponse({
        "slots": [
            {
                "id": s.id,
                "label": f"{s.start_time.strftime('%I:%M %p')} - {s.end_time.strftime('%I:%M %p')}"
            }
            for s in slots
        ]
    })


# ------------------------
# API: BOOK APPOINTMENT
# ------------------------
@api_view(["POST"])
@login_required
def book_appointment(request):
    slot_id = request.data.get("slot_id")
    consultation_type = request.data.get("consultation_type", "ONLINE")

    with transaction.atomic():
        slot = get_object_or_404(
            TimeSlot.objects.select_for_update(),
            id=slot_id,
            is_available=True
        )

        doctor = slot.doctor
        amount = doctor.consultation_fee or 0

        appointment = Appointment.objects.create(
            user=request.user,
            doctor=doctor,
            slot=slot,
            consultation_type=consultation_type,
            amount=amount,
            payment_status="PENDING",
            status="BOOKED",
            payment_mode="ONLINE" if consultation_type == "ONLINE" else "OFFLINE"
        )

        slot.is_available = False
        slot.save()

    # 🏥 CLINIC → CONFIRM ONLY
    if consultation_type == "CLINIC":
        return Response({
            "status": "CONFIRMED",
            "appointment_id": appointment.id,
            "message": f"Appointment booked. Pay Rs. {amount} at clinic."
        })

    # 💳 ONLINE → MUST GO TO PAYMENT
    return Response({
        "status": "PAYMENT_REQUIRED",
        "appointment_id": appointment.id,
        "amount": amount
    })



# ------------------------
# PATIENT: SELECT SLOT (HTML)
# ------------------------
@login_required
def select_slot(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    return render(
        request,
        "appointments/select_slot.html",
        {"doctor": doctor, "today": timezone.now().date()}
    )


# ------------------------
# PATIENT: HISTORY
# ------------------------
@login_required
def appointment_history(request):
    appointments = Appointment.objects.filter(
        user=request.user
    ).select_related("doctor", "slot").order_by("-created_at")

    return render(
        request,
        "appointments/history.html",
        {"appointments": appointments}
    )


# ------------------------
# PATIENT: CANCEL
# ------------------------
@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user,
        status="BOOKED"
    )

    if not appointment.can_cancel():
        return HttpResponseForbidden("Cannot cancel this appointment.")

    slot = appointment.slot
    slot.is_available = True
    slot.save()

    appointment.status = "CANCELLED"
    appointment.save()

    return redirect("appointments:appointment_history")

@login_required
def upload_report(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user
    )

    # Allow upload only after confirmation
    if appointment.consultation_type == "ONLINE" and appointment.payment_status != "PAID":
        return HttpResponseForbidden("Upload after payment")

    if appointment.consultation_type == "CLINIC" and appointment.status != "BOOKED":
        return HttpResponseForbidden("Invalid appointment")

    if request.method == "POST":
        files = request.FILES.getlist("reports")

        for f in files:
            AppointmentReport.objects.create(
                appointment=appointment,
                file=f
            )

        return redirect("appointments:appointment_history")

    return render(
        request,
        "appointments/upload_report.html",
        {"appointment": appointment}
    )

@login_required
def delete_report(request, report_id):
    report = get_object_or_404(
        AppointmentReport,
        id=report_id,
        appointment__user=request.user
    )

    appointment_id = report.appointment.id
    report.file.delete(save=False)  # delete file from storage
    report.delete()

    return redirect("appointments:appointment_history")

from django.http import FileResponse
from pathlib import Path

from pathlib import Path

@login_required
def view_report(request, report_id):
    report = get_object_or_404(
        AppointmentReport,
        id=report_id,
        appointment__user=request.user
    )

    file_ext = Path(report.file.name).suffix.lower()
    is_pdf = file_ext == ".pdf"

    return render(
        request,
        "appointments/view_report.html",
        {
            "report": report,
            "is_pdf": is_pdf
        }
    )

@login_required
def doctor_edit_slot(request, slot_id):
    if not hasattr(request.user, "doctor"):
        return HttpResponseForbidden("Doctor access only")

    slot = get_object_or_404(
        TimeSlot,
        id=slot_id,
        doctor=request.user.doctor
    )

    if not slot.is_available:
        return HttpResponseForbidden("Cannot edit booked slot")

    if request.method == "POST":
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")

        slot.start_time = datetime.strptime(start_time, "%H:%M").time()
        slot.end_time = datetime.strptime(end_time, "%H:%M").time()

        slot.full_clean()  # overlap + validation
        slot.save()

        return redirect(f"?date={slot.date}")

    return render(
        request,
        "doctors/edit_slot.html",
        {"slot": slot}
    )

