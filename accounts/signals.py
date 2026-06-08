from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile

@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, **kwargs):
    profile, _ = Profile.objects.get_or_create(user=instance)

    # Auto-assign ADMIN role for superusers
    if instance.is_superuser and profile.role != "ADMIN":
        profile.role = "ADMIN"
        profile.save()
