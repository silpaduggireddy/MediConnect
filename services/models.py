from django.db import models


class TrainingCourse(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
