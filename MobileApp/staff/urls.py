from django.urls import path
from .views import (
    staff_dashboard,
    staff_doctors,
    staff_appointments,
    doctor_appointments,
    doctor_slots,
    book_clinic_appointment,
    mark_payment_paid,
    update_appointment_status,
    slots_by_date,   # 🔥 ADD THIS
)

app_name = "staff"

urlpatterns = [
    path("dashboard/", staff_dashboard, name="staff_dashboard"),

    path("doctors/", staff_doctors, name="staff_doctors"),
    path("appointments/", staff_appointments, name="staff_appointments"),

    path(
        "doctor/<int:doctor_id>/appointments/",
        doctor_appointments,
        name="staff_doctor_appointments"
    ),

    path(
        "doctor/<int:doctor_id>/slots/",
        doctor_slots,
        name="staff_doctor_slots"
    ),

    # 🔥 AJAX – slots by date
    path(
        "doctor/<int:doctor_id>/slots-by-date/",
        slots_by_date,
        name="slots_by_date"
    ),

    # 🔥 FIX NAME to match template
    path(
        "doctor/<int:doctor_id>/book/",
        book_clinic_appointment,
        name="book_clinic_appointment"
    ),

    path(
        "appointment/<int:id>/pay/",
        mark_payment_paid,
        name="staff_mark_paid"
    ),

    path(
        "appointment/<int:id>/status/",
        update_appointment_status,
        name="staff_update_status"
    ),
]
