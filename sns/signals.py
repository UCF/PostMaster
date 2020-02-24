import logging
from django.dispatch import Signal
from django.dispatch import receiver
from django.conf import settings
from django.db.models.signals import post_save

from sns.models import Bounce, Complaint

from manager.models import Recipient

logger = logging.getLogger(__name__)

# Signal that is fired when a feedback object is created
# This can be a Bounce or Complaint that is processed.
feedback = Signal(providing_args=['instance', 'message'])

@receiver(post_save, sender=Bounce)
def maybe_disable_bounce(sender, instance, raw, using, **kwargs):
    """
    Hooked function for when Bounce objects are created.
    When the object is created, this function checks to see
    if this is a hard bounce or not. If it is a hard bounce,
    the receipient is always disabled. For soft bounces,
    the MAX_BOUNCE_COUNT setting is used to determine if
    the recipient should be disabled.
    """
    try:
        recipient = Recipient.objects.get(email_address=instance.address.lower())
    except Recipient.DoesNotExist:
        logger.warning("The recipient %s could not be found during a disable recipient hook.", instance.address)
        return

    if recipient and instance.hard:
        recipient.disable = True
        recipient.save()
    elif recipient and not instance.hard:
        bounce_count = Bounce.objects.filter(address=instance.address).count()

        if bounce_count > settings.MAX_BOUNCE_COUNT:
            recipient.disable = True
            recipient.save()

@receiver(post_save, sender=Complaint)
def maybe_disable_complaint(sender, instance, raw, using, **kwargs):
    """
    Hooked function for when Complaint objects are created.
    If the recpient that issued the complain can be found,
    that recipient is disabled.
    """
    try:
        recipient = Recipient.objects.get(email_address=instance.address.lower())
    except Recipient.DoesNotExist:
        logger.warning("The recipient %s could not be found during a disable recipient hook.", instance.address)
        return

    if recipient:
        recipient.disable = True
        recipient.save()

