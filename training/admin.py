from django.contrib import admin
from .models import TrainingEnrollment

@admin.register(TrainingEnrollment)
class TrainingEnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "course",
        "phone",
        "email",
        "enrolled_at"
    )
    list_filter = ("course",)
    search_fields = ("full_name", "phone", "email")
