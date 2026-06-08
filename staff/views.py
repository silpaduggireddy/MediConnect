import json
from datetime import datetime,timedelta
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
    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)
    max_date = today + timedelta(days=3)
    return render(request, "staff/select_slot.html", {
        "doctor": doctor,
        "min_date": tomorrow,
        "max_date" : max_date  
        
    })


# -------------------------
# DOWNLOAD APPOINTMENTS (FILTERED OR ALL BASED ON AVAILABILITY)
# -------------------------
@login_required
def download_appointments(request, doctor_id):
    if not staff_only(request):
        return redirect("phone_register")

    from reportlab.lib.pagesizes import landscape
    from reportlab.lib.units import inch

    doctor = get_object_or_404(Doctor, id=doctor_id)
    selected_date = request.GET.get("date")
    sort = request.GET.get("sort", "desc")
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            selected_date = None

    appointments = Appointment.objects.filter(doctor=doctor)
    if selected_date:
        appointments = appointments.filter(slot__date=selected_date)

    appointments = appointments.order_by(
        "created_at" if sort == "asc" else "-created_at"
    )

    buffer = BytesIO()

    # ✅ Landscape page
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))

    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"Appointments for {doctor.name}", styles["Heading2"]))

    # ✅ Table header
    data = [[
        "S.No.", "Patient Name", "Age", 
         "Current Problem",
        "Contact", "Slot", "Booked On", "Status", "Payment"
    ]]

    # ✅ Table rows
    for idx, appt in enumerate(appointments, start=1):

        slot_text = "-"
        if appt.slot:
            slot_text = f"{appt.slot.date} {appt.slot.start_time.strftime('%I:%M %p')} - {appt.slot.end_time.strftime('%I:%M %p')}"

        data.append([
            str(idx),
            str(appt.patient_name or "-"),
            str(appt.age or "-"),
            str(appt.comments or "-"),
            str(appt.contact_number or "-"),
            slot_text,
            appt.created_at.strftime("%Y-%m-%d"),
            str(appt.status or "-"),
            str(appt.payment_status or "-"),
        ])

    # ✅ Column widths (alignment fix)
    table = Table(
        data,
        colWidths=[
            0.5*inch,
            1.2*inch,
            0.5*inch,
            1.8*inch,
            1.2*inch,
            2*inch,
            1.2*inch,
            1*inch,
            1*inch
        ],
        repeatRows=1
    )

    # ✅ Table style
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),

        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),

        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)

    return FileResponse(
        buffer,
        as_attachment=True,
        filename = f"appointments_{doctor_id}_{selected_date}.pdf" if selected_date else f"appointments_{doctor_id}.pdf"
    )

@login_required
def book_clinic_appointment(request, doctor_id):
    if not staff_only(request):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    data = json.loads(request.body)
    slot_id = data.get("slot_id")
    patient_name = data.get("patient_name")
    age = data.get("age")
    # gender = data.get("gender")
    # health_history = data.get("health_history")
    comments = data.get("comments")
    contact_number = data.get("contact_number")


    slot = get_object_or_404(TimeSlot, id=slot_id, is_available=True)
    today = timezone.localdate()
    min_date = today + timedelta(days=1)
    max_date = today + timedelta(days=3)
    # 🔥 DATE VALIDATION
    if slot.date <= today:
         return JsonResponse({"message": "Today booking  not allowed"}, status=400)
    if slot.date.weekday() == 6:
         return JsonResponse({"message": "Sunday appointmentsnot allowed"},status=400)
    if slot.date > max_date:
          return JsonResponse({"message": "Only next 3 days allowed"}, status=400)
    
    user = request.user
    Appointment.objects.create(
        user=user,  # Important
        doctor=slot.doctor,
        slot=slot,
        consultation_type="CLINIC",
        amount=slot.doctor.consultation_fee,
        payment_mode="OFFLINE",
        payment_status="PENDING",
        status="BOOKED",
        patient_name=patient_name,
        age=age,
        # gender=gender,
        # health_history=health_history,
        comments=comments,
        contact_number=contact_number,
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

    appointment_type = request.GET.get("type", "ONLINE")
    print("TYPE =", appointment_type)

    # 🔥 delete ALL slots for that date
    TimeSlot.objects.filter(
        doctor=doctor,
        date=selected_date,
        slot_type=appointment_type
    ).delete()

    # ✅ CLINIC = 15 mins
    if appointment_type == "CLINIC":

        start_time = datetime.combine(selected_date, datetime.strptime("07:30", "%H:%M").time())
        end_time = datetime.combine(selected_date, datetime.strptime("13:00", "%H:%M").time())

        while start_time < end_time:

            slot_end = start_time + timedelta(minutes=15)

            TimeSlot.objects.get_or_create(
                doctor=doctor,
                date=selected_date,
                start_time=start_time.time(),
                end_time=slot_end.time(),
                defaults={
                    "is_available": True,
                    "slot_type": "CLINIC"
                }
            )

            start_time = slot_end

    # ✅ ONLINE = 15 mins
    else:

        start_time = datetime.combine(
            selected_date,
            datetime.strptime("20:30", "%H:%M").time()
        )

        end_time = datetime.combine(
           selected_date,
           datetime.strptime("21:30", "%H:%M").time()
        )

        while start_time < end_time:

            slot_end = start_time + timedelta(minutes=15)

            TimeSlot.objects.get_or_create(
                doctor=doctor,
                date=selected_date,
                start_time=start_time.time(),
                end_time=slot_end.time(),
                defaults={
                    "is_available":True,
                    "slot_type":"ONLINE"
                }
            )

            start_time = slot_end

    slots = TimeSlot.objects.filter(
        doctor=doctor,
        date=selected_date,
        is_available=True,
        slot_type=appointment_type

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
    
    user = request.user
    phone = request.POST.get("contact_number")
    
    Appointment.objects.create(
        user=user,
        doctor=slot.doctor,
        slot=slot,
        booked_by_staff=request.user,   # ✅ STAFF BOOKING
        patient_name=request.POST.get("patient_name") or "Walk-in Patient",
        age=request.POST.get("age") or None,
        comments=request.POST.get("comments"),
        contact_number=phone,
        consultation_type="CLINIC",
        amount=slot.doctor.consultation_fee,
        payment_mode="OFFLINE",
        payment_status="PENDING",
        status="BOOKED",
    )

    slot.is_available = False
    slot.save()

    return redirect("staff_dashboard")
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

@csrf_exempt
def check_user(request):
    data = json.loads(request.body)
    mobile = data.get("mobile")

    User = get_user_model()

    exists = (
        User.objects.filter(username=mobile).exists()
        or Appointment.objects.filter(contact_number=mobile).exists()
    )

    if exists:
        return JsonResponse({"status": "exists"})  # block register

    return JsonResponse({"status": "new"})  # allow register
@csrf_exempt
def login_check_user(request):
    data = json.loads(request.body)
    mobile = data.get("mobile")

    User = get_user_model()

    if User.objects.filter(username=mobile).exists():
        return JsonResponse({"status": "exists"})  # OTP allow
    else:
        return JsonResponse({"status": "not_registered"})  # block OTP
