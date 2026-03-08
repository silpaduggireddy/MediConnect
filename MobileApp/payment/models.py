from django.db import models

class Payment(models.Model):
    appointment = models.OneToOneField("appointments.Appointment", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    method = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default="SUCCESS")
