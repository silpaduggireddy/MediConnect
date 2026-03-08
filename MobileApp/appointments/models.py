from django.db import models
from doctors.models import Doctor
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime

User = get_user_model()

# -----------------------
# CONSTANTS
# -----------------------
CONSULTATION_TYPE_CHOICES = [
    ("ONLINE", "Online Consultation"),
    ("CLINIC", "Clinic Consultation"),
]

APPOINTMENT_STATUS_CHOICES = [
    ("BOOKED", "Booked"),
    ("COMPLETED", "Completed"),
    ("CANCELLED", "Cancelled"),
]

PAYMENT_MODE_CHOICES = [
    ("ONLINE", "Online Payment"),
    ("OFFLINE", "Pay at Clinic"),
]

PAYMENT_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("PAID", "Paid"),
    ("FAILED", "Failed"),
    ("UNPAID", "Unpaid"),
]

# -----------------------
# TIME SLOT
# -----------------------
class TimeSlot(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="timeslots"
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    def clean(self):
        # start < end
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time")

        # no past dates
        if self.date < timezone.localdate():
            raise ValidationError("Cannot create slots for past dates")

        # prevent overlapping slots
        overlapping = TimeSlot.objects.filter(
            doctor=self.doctor,
            date=self.date,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exclude(id=self.id)

        if overlapping.exists():
            raise ValidationError("This slot overlaps with an existing slot")

    def __str__(self):
        return f"{self.doctor.name} | {self.date} {self.start_time}-{self.end_time}"

# -----------------------
# APPOINTMENT
# -----------------------
class Appointment(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    slot = models.OneToOneField(TimeSlot, on_delete=models.CASCADE)

    consultation_type = models.CharField(
        max_length=10,
        choices=CONSULTATION_TYPE_CHOICES,
        default="ONLINE"
    )

    booked_by_staff = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="staff_appointments"
    )

    amount = models.DecimalField(max_digits=8, decimal_places=2)

    payment_mode = models.CharField(
        max_length=10,
        choices=PAYMENT_MODE_CHOICES,
        default="OFFLINE"
    )

    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default="UNPAID"
    )

    status = models.CharField(
        max_length=10,
        choices=APPOINTMENT_STATUS_CHOICES,
        default="BOOKED"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_past(self):
        slot_dt = datetime.combine(self.slot.date, self.slot.start_time)
        slot_dt = timezone.make_aware(slot_dt)
        return timezone.now() >= slot_dt

    def can_cancel(self):
        return self.status == "BOOKED" and not self.is_past

# -----------------------
# REPORT
# -----------------------
class AppointmentReport(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="reports"
    )
    file = models.FileField(upload_to="appointment_reports/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for Appointment #{self.appointment.id}"
