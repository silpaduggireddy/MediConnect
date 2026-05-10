from django.urls import path
from .views import (
    doctor_dashboard,
    doctor_appointments,
    doctor_slots,
    doctor_edit_slot,
    doctor_mark_completed,
    delete_slot,
    doctor_list,
    doctor_view_reports,
)

app_name = "doctors"

urlpatterns = [
    # Doctor-only
    path("dashboard/", doctor_dashboard, name="doctor_dashboard"),
    path("appointments/", doctor_appointments, name="doctor_appointments"),
    path("slots/", doctor_slots, name="doctor_slots"),
    path("slots/<int:slot_id>/edit/", doctor_edit_slot, name="doctor_edit_slot"),
    path("slots/<int:slot_id>/delete/", delete_slot, name="delete_slot"),
    path(
        "appointments/<int:appointment_id>/complete/",
        doctor_mark_completed,
        name="doctor_mark_completed"
    ),

    # User-facing
    path("", doctor_list, name="doctor_list"),
    path(
    "appointments/<int:appointment_id>/reports/",
    doctor_view_reports,
    name="doctor_view_reports"
),

]
