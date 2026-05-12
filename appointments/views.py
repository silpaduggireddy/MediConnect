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
from django.http import HttpResponse


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
    #  ✅ Only Tuesday, Wednesday, Thursday
    if slot_date.weekday() not in [1, 2, 3]:
        return

    # ✅ ONLINE SLOT TIMING
    current = datetime.combine(slot_date, time(20, 30))   # 8:30 PM
    end_dt = datetime.combine(slot_date, time(21, 30))    # 9:30 PM

    while current < end_dt:

        slot_end = current + timedelta(minutes=15)

        TimeSlot.objects.get_or_create(
            doctor=doctor,
            date=slot_date,
            start_time=current.time(),
            end_time=slot_end.time(),
            defaults={"is_available": True}
        )

        current = slot_end

def generate_clinic_slots(doctor, slot_date):

    slot_duration = timedelta(minutes=15)

    # Morning
    start_time = datetime.combine(slot_date, time(7, 30))
    end_time = datetime.combine(slot_date, time(13, 0))

    while start_time < end_time:

        slot_end = start_time + slot_duration

        TimeSlot.objects.get_or_create(
            doctor=doctor,
            date=slot_date,
            start_time=start_time.time(),
            end_time=slot_end.time(),
            defaults={"is_available": True}
        )

        start_time = slot_end

    # Afternoon
    start_time = datetime.combine(slot_date, time(14, 0))
    end_time = datetime.combine(slot_date, time(15, 0))

    while start_time < end_time:

        slot_end = start_time + slot_duration

        TimeSlot.objects.get_or_create(
            doctor=doctor,
            date=slot_date,
            start_time=start_time.time(),
            end_time=slot_end.time(),
            defaults={"is_available": True}
        )

        start_time = slot_end
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

    appointment_type = request.GET.get("type", "ONLINE")

    # ✅ CLINIC = 15 mins
    if appointment_type == "CLINIC":

        TimeSlot.objects.filter(
            doctor=doctor,
            date=selected_date,
            is_available=True
        ).delete()

        generate_clinic_slots(doctor, selected_date)

    # ✅ ONLINE = 30 mins
    else:
        # Delete old slots
        TimeSlot.objects.filter(
            doctor=doctor,
            date=selected_date,
            is_available=True
        ).delete()

        # Generate ONLINE slots
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
    if slot_id == "No slots available":
         return Response(
             {"error": "No slots available"},
             status=400
    )

    try:
        slot_id = int(slot_id)
    except:
        return Response(
        {"error": "Invalid slot id"},
        status=400
    )
    consultation_type = request.data.get("consultation_type", "ONLINE")
    patient_name = request.data.get("patient_name")
    age = request.data.get("age")
   # gender = request.data.get("gender")
    # health_history= request.data.get("health_history")
    current_health_problem = request.data.get("current_health_problem")
    whatsapp_number = request.data.get("whatsapp_number")


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
            patient_name=patient_name,
            age=age,
           # gender=gender,
            # health_history=health_history,
            current_health_problem=current_health_problem,
            whatsapp_number=whatsapp_number,
            amount=amount,
            payment_status="PENDING",
            status="BOOKED",
            payment_mode="ONLINE" if consultation_type == "ONLINE" else "OFFLINE"
        )

        slot.is_available = False
        slot.save()
    # 🏥 CLINIC → CONFIRM ONLY
    if consultation_type == "CLINIC":
             print("test me")
             print(slot.doctor)
             return Response({
                "status": "CONFIRMED",
                "appointment_id": appointment.id,
                "message":  (
                    f"✅ Appointment Booked Successfully\n\n"
                    f"👨‍⚕️ Doctor: Dr. {doctor.name}\n"
                    f"🩺 Specialization: {doctor.specialization}\n"
                    f"🧑 Patient: {appointment.patient_name}\n"
                    f"📅 Date: {appointment.slot.date}\n"
                    f"⏰ Time: {appointment.slot.start_time}\n"
                    f"💰 Pay Rs. {amount} at clinic."
        )
                    
    
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
        whatsapp_number=request.user.username
    ).select_related("doctor", "slot").order_by("-slot__date", "slot__start_time")

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
    if appointment.is_past:
        return HttpResponseForbidden("Cannot cancel past appointments")

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

from django.contrib import messages
from django.shortcuts import redirect

from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from reportlab.pdfgen import canvas
from io import BytesIO
from .models import Appointment

@login_required
def download_invoice(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, user=request.user)

    # Allow download only after confirmation
    if appointment.consultation_type == "ONLINE" and appointment.payment_status != "PAID":
        return HttpResponseForbidden("Download after appointment confirmation")

    if appointment.consultation_type == "CLINIC" and appointment.status != "BOOKED":
        return HttpResponseForbidden("Invalid appointment")

    # Create PDF in memory
    buffer = BytesIO()
    p = canvas.Canvas(buffer)

    # Example content
    p.setFont("Helvetica", 14)
    p.drawString(100, 750, "Appointment Confirmation")
    p.setFont("Helvetica", 12)
    p.drawString(100, 720, f"Appointment ID: {appointment.id}")
    p.drawString(100, 700, f"Doctor: {appointment.doctor.name}")
    p.drawString(100, 680, f"Patient: {appointment.patient_name}")
    p.drawString(100, 660, f"Consultation Type: {appointment.consultation_type}")
    p.drawString(100, 640, f"Date: {appointment.slot.date}")
    p.drawString(100, 620, f"Time: {appointment.slot.start_time}-{appointment.slot.end_time}")
    p.drawString(100, 600, f"Status: {appointment.status}")
    p.drawString(100, 580, f"Payment Status: {appointment.payment_status}")

    p.showPage()
    p.save()

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"appointment_{appointment.patient_name}_{appointment.slot}.pdf")


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

@login_required
def view_reports_by_appointment(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user
    )

    reports = appointment.reports.all()

    return render(
        request,
        "appointments/view_all_reports.html",
        {
            "appointment": appointment,
            "reports": reports
        }
    )