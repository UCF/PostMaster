import logging
from django.dispatch import Signal
from django.dispatch import receiver
from django.db.models.signals import post_save

from sns.models import Bounce

from manager.models import Recipient

logger = logging.getLogger(__name__)

notification = Signal(providing_args=['notification', 'request'])

feedback = Signal(providing_args=['instance', 'message'])

@receiver(post_save, sender=Bounce)
def maybe_disable_bounce(sender, instance, raw, using, **kwargs):
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
