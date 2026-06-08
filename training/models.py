from django.db import models
from django.contrib import admin
from django.contrib.auth import get_user_model


class TrainingCourse(models.Model):
    name = models.CharField(max_length=100)

    trainer_name = models.CharField(max_length=100)

    STATUS_CHOICES = [
        ("UPCOMING", "Upcoming"),
        ("ONGOING", "Ongoing"),
        ("COMPLETED", "Completed"),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="UPCOMING"
    )

    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    def __str__(self):
        return self.name

@admin.register(TrainingCourse)
class TrainingCourseAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "trainer_name",
        "status",
        "start_datetime",
        "end_datetime",
    )
    list_filter = ("status",)



User = get_user_model()

class TrainingEnrollment(models.Model):
    course = models.ForeignKey(
        TrainingCourse,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()

    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "user")

    def __str__(self):
        return f"{self.full_name} → {self.course.name}"
