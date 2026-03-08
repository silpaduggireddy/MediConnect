
from django.urls import path
from . import views
from .views import appointment_history, cancel_appointment,select_slot, book_appointment,available_slots_by_date,upload_report,delete_report

app_name = "appointments"

urlpatterns = [
    path("", views.select_slot, name="appointment_home"),
    path("slots/<int:doctor_id>/", select_slot, name="select_slot"),
    path("book/", book_appointment, name="book_appointment"),
    path("history/", appointment_history, name="appointment_history"),
    path("cancel/<int:appointment_id>/", cancel_appointment, name="cancel_appointment"),
    path(
        "doctor/<int:doctor_id>/slots-by-date/",
        available_slots_by_date,
        name="slots_by_date"
    ),
    path("appointments/<int:appointment_id>/upload-report/",upload_report,name="upload_report"),
    path("reports/<int:report_id>/delete/",delete_report,name="delete_report"),
    path("reports/<int:report_id>/view/",views.view_report,name="view_report"),
]
