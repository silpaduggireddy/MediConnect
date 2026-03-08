import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from doctors.models import Doctor
from appointments.models import Appointment, TimeSlot

from io import BytesIO
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet


# -------------------------
# Helper
# -------------------------
def staff_only(request):
    return (
        request.user.is_authenticated and
        hasattr(request.user, "profile") and
        request.user.profile.role == "STAFF"
    )


# -------------------------
# DASHBOARD
# -------------------------
@login_required
def staff_dashboard(request):
    if not staff_only(request):
        return redirect("phone_register")
    return render(request, "staff/dashboard.html")


# -------------------------
# DOCTORS → BOOKING FLOW
# -------------------------
@login_required
def staff_doctors(request):
    if not staff_only(request):
        return redirect("phone_register")

    doctors = Doctor.objects.filter(is_active=True)
    return render(request, "staff/doctors.html", {"doctors": doctors})


@login_required
def doctor_slots(request, doctor_id):
    if not staff_only(request):
        return redirect("phone_register")

    doctor = get_object_or_404(Doctor, id=doctor_id)
    return render(request, "staff/select_slot.html", {
        "doctor": doctor,
        "today": timezone.now().date()
    })


# -------------------------
# DOWNLOAD APPOINTMENTS (FILTERED OR ALL BASED ON AVAILABILITY)
# -------------------------
@login_required
def download_appointments(request, doctor_id):
    if not staff_only(request):
        return redirect("phone_register")

    doctor = get_object_or_404(Doctor, id=doctor_id)
    selected_date = request.GET.get("date")
    sort = request.GET.get("sort", "desc")

    appointments = Appointment.objects.filter(doctor=doctor)
    if selected_date:
        appointments = appointments.filter(slot__date=selected_date)

    appointments = appointments.order_by(
        "created_at" if sort == "asc" else "-created_at"
    )

    # Debug: print appointments in console
    print("Appointments:", list(appointments.values()))

    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"Appointments for {doctor.name}", styles["Heading1"]))

    # Table header
    data = [
        ["S.No.", "Patient Name", "Age", "Gender", "Previous Problem",
         "Current Problem", "Whatsapp", "Slot", "Booked On", "Status", "Payment"]
    ]

    # Table rows
    for idx, appt in enumerate(appointments, start=1):
        
        # print(appointments.count)
        data.append([
            idx,
            appt.patient_name,
            appt.age,
            appt.gender,
            appt.previous_health_problem,
            appt.current_health_problem,
            appt.whatsapp_number,
            appt.slot,
            appt.created_at.strftime("%Y-%m-%d"),
            appt.status,
            appt.payment_status,
        ])

    # Build table
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"appointments_{doctor_id}.pdf")

@login_required
def book_clinic_appointment(request, doctor_id):
    if not staff_only(request):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    data = json.loads(request.body)
    slot_id = data.get("slot_id")

    slot = get_object_or_404(TimeSlot, id=slot_id, is_available=True)

    Appointment.objects.create(
        user=None,  # walk-in
        doctor=slot.doctor,
        slot=slot,
        consultation_type="CLINIC",
        amount=slot.doctor.consultation_fee,
        payment_mode="PAY_AT_CLINIC",
        payment_status="PENDING",
        status="BOOKED"
    )

    slot.is_available = False
    slot.save()

    return JsonResponse({
        "success": True,
        "message": "Clinic appointment booked successfully"
    })


# -------------------------
# APPOINTMENTS (FILTERED)
# -------------------------
@login_required
def doctor_appointments(request, doctor_id):
    if not staff_only(request):
        return redirect("phone_register")

    doctor = get_object_or_404(Doctor, id=doctor_id)
    selected_date = request.GET.get("date")
    sort = request.GET.get("sort", "desc")

    appointments = Appointment.objects.filter(doctor=doctor)

    if selected_date:
        appointments = appointments.filter(slot__date=selected_date)

    appointments = appointments.order_by(
        "created_at" if sort == "asc" else "-created_at"
    )

    return render(request, "staff/doctor_appointments.html", {
        "doctor": doctor,
        "appointments": appointments,
        "selected_date": selected_date,
        "sort": sort,
    })


# -------------------------
# ACTIONS
@login_required
@require_POST
def mark_payment_paid(request, id):
    if not staff_only(request):
        return redirect("phone_register")

    appointment = get_object_or_404(Appointment, id=id)

    # 🔐 SAFETY: Only allow CLINIC payments to be marked paid
    if appointment.consultation_type == "CLINIC":
        appointment.payment_status = "PAID"
        appointment.save()

    # 🔥 Redirect back to same page
    return redirect(request.META.get("HTTP_REFERER", "staff:staff_dashboard"))

@login_required
def update_appointment_status(request, id):
    if not staff_only(request):
        return redirect("phone_register")

    appointment = get_object_or_404(Appointment, id=id)
    status = request.POST.get("status")

    if status in ["COMPLETED", "CANCELLED"]:
        appointment.status = status
        appointment.save()

    next_url = request.GET.get("next")
    return redirect(next_url or "staff:staff_dashboard")


# -------------------------
# AJAX
# -------------------------
def slots_by_date(request, doctor_id):
    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse({"slots": []})

    selected_date = datetime.fromisoformat(date_str).date()
    doctor = get_object_or_404(Doctor, id=doctor_id)

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
            } for s in slots
        ]
    })

@login_required
def staff_appointments(request):
    if not staff_only(request):
        return redirect("phone_register")

    doctors = Doctor.objects.filter(is_active=True)
    return render(request, "staff/appointments.html", {
        "doctors": doctors
    })


@login_required
def book_appointment_staff(request, slot_id):
    slot = get_object_or_404(
        TimeSlot,
        id=slot_id,
        is_available=True
    )

    Appointment.objects.create(
        doctor=slot.doctor,
        slot=slot,
        booked_by_staff=request.user,   # ✅ STAFF BOOKING
    )

    slot.is_available = False
    slot.save()

    return redirect("staff_dashboard")
