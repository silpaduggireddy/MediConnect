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

   # ✅ ONLINE only on Tue, Wed, Thu
    if slot_date.weekday() not in [1, 2, 3]:
        return
    
    # ❌ Holidays
    if slot_date in HOLIDAYS:
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

    # No past dates
    if slot_date < timezone.localdate():
        return

    # Sunday holiday
    if slot_date.weekday() == 6:
        return

    # Custom holidays
    if slot_date in HOLIDAYS:
        return

    slot_duration = timedelta(minutes=15)

    # =========================
    # MORNING: 7:30 AM → 12:00 PM
    # =========================

    start_time = datetime.combine(slot_date, time(7, 30))
    end_time = datetime.combine(slot_date, time(12, 0))

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

    # =========================
    # AFTERNOON: 1:00 PM → 3:00 PM
    # =========================

    start_time = datetime.combine(slot_date, time(13, 0))
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

        return JsonResponse({
            "slots": []
        })

    try:

        selected_date = datetime.strptime(
            date_str,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        return JsonResponse({
            "slots": []
        })

    doctor = get_object_or_404(
        Doctor,
        id=doctor_id
    )

    appointment_type = request.GET.get(
        "type",
        "ONLINE"
    )

    # ❌ SUNDAY HOLIDAY
    if selected_date.weekday() == 6:

        return JsonResponse({
            "slots": []
        })

    # ❌ CUSTOM HOLIDAYS
    if selected_date in HOLIDAYS:

        return JsonResponse({
            "slots": []
        })

    # =========================
    # ONLINE → Tue/Wed/Thu
    # =========================

    if appointment_type == "ONLINE":

        if selected_date.weekday() not in [1, 2, 3]:

            return JsonResponse({
                "slots": []
            })

        generate_default_slots(
            doctor,
            selected_date
        )

    # =========================
    # CLINIC → Saturday
    # =========================

    elif appointment_type == "CLINIC":

        if selected_date.weekday() == 6:

            return JsonResponse({
                "slots": []
            })

        generate_clinic_slots(
            doctor,
            selected_date
        )

    if appointment_type == "ONLINE":
        slots = TimeSlot.objects.filter(
        doctor=doctor,
        date=selected_date,
        is_available=True,
        start_time__gte=time(20, 30),
        end_time__lte=time(21, 30)
    ).order_by("start_time")

    else:  # CLINIC
        slots = TimeSlot.objects.filter(
        doctor=doctor,
        date=selected_date,
        is_available=True,
        start_time__gte=time(7, 30),
        end_time__lte=time(15, 0)
    ).order_by("start_time")

    return JsonResponse({

        "slots": [

            {
                "id": s.id,

                "label":
                    f"{s.start_time.strftime('%I:%M %p')} - "
                    f"{s.end_time.strftime('%I:%M %p')}"
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
    slot_ids = request.data.get("slot_ids")
    if not slot_ids:
       return Response(
          {"error": "No slots selected"},
          status=400
    )
    if not isinstance(slot_ids, list):
        slot_ids = [slot_ids]
    consultation_type = request.data.get("consultation_type", "ONLINE")
    patient_name = request.data.get("patient_name")
    age = request.data.get("age")
   # gender = request.data.get("gender")
    # health_history= request.data.get("health_history")
    comments = request.data.get("comments")
    contact_number = request.data.get("contact_number")
    reschedule_id = request.data.get("reschedule_id")

    with transaction.atomic():
        slot = get_object_or_404(
            TimeSlot.objects.select_for_update(),
            id=slot_ids[0],
            is_available=True
        )

        doctor = slot.doctor
        amount = doctor.consultation_fee or 0

        if reschedule_id:
            old_appointment = get_object_or_404(
                Appointment,
                id=reschedule_id,
                user=request.user,
                status="BOOKED"
            )

            appointment_datetime = timezone.make_aware(
                datetime.combine(
                    old_appointment.slot.date,
                    old_appointment.slot.start_time
                )
            )

            if appointment_datetime - timezone.now() < timedelta(hours=12):
                return Response(
                    {
                        "error": "Appointments can only be rescheduled at least 12 hours before the slot."
                    },
                    status=400
                )

            old_slot = old_appointment.slot
            old_slot.is_available = True
            old_slot.save()

            old_appointment.slot = slot
            old_appointment.consultation_type = consultation_type
            old_appointment.patient_name = patient_name
            old_appointment.age = age
            old_appointment.comments = comments
            old_appointment.contact_number = contact_number
            old_appointment.payment_mode = "ONLINE" if consultation_type == "ONLINE" else "OFFLINE"
            old_appointment.save()

            appointment = old_appointment
        else:
            appointment = Appointment.objects.create(
                user=request.user,
                doctor=doctor,
                slot=slot,
                consultation_type=consultation_type,
                patient_name=patient_name,
                age=age,
                comments=comments,
                contact_number=contact_number,
                amount=amount,
                payment_status="PENDING",
                status="BOOKED",
                payment_mode="ONLINE" if consultation_type == "ONLINE" else "OFFLINE"
            )

        slot.is_available = False
        slot.save()

    if consultation_type == "CLINIC":
        return Response({
            "status": "CONFIRMED",
            "appointment_id": appointment.id,
            "message": (
                f"Appointment Booked Successfully\n\n"
                f"Doctor: Dr. {doctor.name}\n"
                f"Specialization: {doctor.specialization}\n"
                f"Patient: {appointment.patient_name}\n"
                f"Date: {appointment.slot.date}\n"
                f"Time: {appointment.slot.start_time}\n"
                f"Pay Rs. {amount} at clinic."
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
        user=request.user
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

    # Prevent cancelling past appointments
    if appointment.is_past:

        return HttpResponseForbidden(
            "Cannot cancel past appointments"
        )

    # Appointment datetime
    appointment_datetime = timezone.make_aware(
        datetime.combine(
            appointment.slot.date,
            appointment.slot.start_time
        )
    )

    # Current time
    now = timezone.now()

    # Time difference
    time_difference = appointment_datetime - now

    # Allow only before 12 hours
    if time_difference < timedelta(hours=12):

        return HttpResponseForbidden(
            "Appointments can only be cancelled at least 12 hours before the slot."
        )

    # Free the slot
    slot = appointment.slot

    slot.is_available = True
    slot.save()

    # Cancel appointment
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

@login_required
def reschedule_appointment(request, appointment_id):

    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user,
        status="BOOKED"
    )

    # Prevent rescheduling past appointments
    if appointment.is_past:

        return HttpResponseForbidden(
            "Cannot reschedule past appointments"
        )

    # Appointment datetime
    appointment_datetime = timezone.make_aware(
        datetime.combine(
            appointment.slot.date,
            appointment.slot.start_time
        )
    )

    # Current time
    now = timezone.now()

    # Time difference
    time_difference = appointment_datetime - now

    # Allow only before 12 hours
    if time_difference < timedelta(hours=12):

        return HttpResponseForbidden(
            "Appointments can only be rescheduled at least 12 hours before the slot."
        )

    if request.method == "POST":

        new_slot_id = request.POST.get("slot_id")

        if not new_slot_id:

            return HttpResponseForbidden(
                "No slot selected"
            )

        with transaction.atomic():

            # Lock new slot
            new_slot = get_object_or_404(
                TimeSlot.objects.select_for_update(),
                id=new_slot_id,
                is_available=True
            )

            # OLD SLOT
            old_slot = appointment.slot

            # Make old slot available
            old_slot.is_available = True
            old_slot.save()

            # Assign new slot
            appointment.slot = new_slot
            appointment.save()

            # Mark new slot unavailable
            new_slot.is_available = False
            new_slot.save()

        return redirect("appointments:appointment_history")

    # Show available slots of same doctor
    slots = TimeSlot.objects.filter(
        doctor=appointment.doctor,
        date__gte=timezone.localdate(),
        is_available=True
    ).order_by("date", "start_time")

    return render(
        request,
        "appointments/reschedule_appointment.html",
        {
            "appointment": appointment,
            "slots": slots
        }
    )
