from django.db.models.signals import post_save
from django.dispatch import receiver
from accounts.models import Profile

@receiver(post_save, sender=Doctor)
def set_doctor_role(sender, instance, created, **kwargs):
    if created:
        profile = instance.user.profile
        profile.role = "DOCTOR"
        profile.save()

