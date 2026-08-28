from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Profile

@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(
            user=instance,
            role=Profile.Role.DEVELOPER if instance.is_superuser else Profile.Role.CREW,
        )
    else:
        Profile.objects.get_or_create(user=instance)