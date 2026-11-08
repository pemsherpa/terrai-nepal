from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from forests.models import UserRole

from .models import Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance: User, created: bool, **kwargs) -> None:
    if created:
        Profile.objects.create(
            user=instance,
            full_name=instance.first_name or "",
        )
        UserRole.objects.get_or_create(user=instance, role=UserRole.Role.USER)
