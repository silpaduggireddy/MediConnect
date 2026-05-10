from django.core.management.base import BaseCommand
from datetime import datetime, time, timedelta, date

from doctors.models import Doctor
from appointments.models import TimeSlot


class Command(BaseCommand):
    help = "Create default 30-min slots (10–12, 1–5) for all doctors"

    def handle(self, *args, **kwargs):
        today = date.today()

        # Define slot ranges
        morning_start = time(10, 0)
        morning_end = time(12, 0)

        afternoon_start = time(13, 0)
        afternoon_end = time(17, 0)

        slot_duration = timedelta(minutes=30)

        doctors = Doctor.objects.filter(is_active=True)

        for doctor in doctors:
            self.stdout.write(f"Creating slots for {doctor.name}")

            self.create_slots(
                doctor, today,
                morning_start, morning_end, slot_duration
            )
            self.create_slots(
                doctor, today,
                afternoon_start, afternoon_end, slot_duration
            )

        self.stdout.write(self.style.SUCCESS("✅ Default slots created successfully"))

    def create_slots(self, doctor, slot_date, start_time, end_time, duration):
        current = datetime.combine(slot_date, start_time)
        end = datetime.combine(slot_date, end_time)

        while current < end:
            next_time = current + duration

            TimeSlot.objects.get_or_create(
                doctor=doctor,
                date=slot_date,
                start_time=current.time(),
                end_time=next_time.time(),
                defaults={"is_available": True}
            )

            current = next_time

