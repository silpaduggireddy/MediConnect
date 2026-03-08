from django.contrib import admin
from .models import TrainingCourse

@admin.register(TrainingCourse)
class TrainingCourseAdmin(admin.ModelAdmin):
    list_display = ("name", "start_datetime", "end_datetime", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    