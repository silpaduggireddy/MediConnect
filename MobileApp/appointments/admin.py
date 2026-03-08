from django.contrib import admin
from .models import TimeSlot

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = (
        "doctor",
        "date",
        "start_time",
        "end_time",
        "is_available",
    )

    list_filter = (
        "doctor",
        "date",
        "is_available",
    )

    search_fields = (
        "doctor__name",
    )

    ordering = ("date", "start_time")
