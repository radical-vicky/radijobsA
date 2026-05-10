from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserWallet


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_wallet(sender, instance, created, **kwargs):
    """Create a wallet for every new user"""
    if created:
        UserWallet.objects.get_or_create(user=instance)