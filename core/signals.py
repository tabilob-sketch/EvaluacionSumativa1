from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Account

@receiver(post_save, sender=User)
def create_account_for_user(sender, instance, created, **kwargs):
    """
    Cuando se crea un User, generar su Account asociado automáticamente
    si no existe. Quedará con organization=None y rol MEMBER.
    """
    if created:
        Account.objects.get_or_create(
            user=instance,
            defaults={"organization": None, "role": Account.Role.MEMBER}
        )
