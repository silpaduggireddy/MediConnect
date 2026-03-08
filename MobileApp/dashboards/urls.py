from django.urls import path
from .views import (
    dashboard_redirect,
    patient_dashboard,
    staff_dashboard,
    doctor_appointments,
    doctor_appointment_history
)

urlpatterns = [
    path("", dashboard_redirect, name="dashboard"),
    path("patient/", patient_dashboard, name="patient_dashboard"),
    path("staff/", staff_dashboard, name="staff_dashboard"),
    path("doctor/appointments/", doctor_appointments, name="doctor_appointments"),
    path("doctor/appointments/<int:appointment_id>/history/",
         doctor_appointment_history,
         name="doctor_appointment_history"),
]
