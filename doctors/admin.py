from django.contrib import admin
from .models import Doctor

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("name", "specialization", "experience_years", "consultation_fee")
    search_fields = ("name", "specialization")
    list_filter = ("specialization", "is_active")
    ordering = ("name",)
    list_display = (
        "name",
        "specialization",
        "experience_years",
        "consultation_fee",
        "is_active",
    )