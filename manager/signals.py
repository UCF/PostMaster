from django.db.models.signals import pre_save
from django.dispatch import receiver

from manager.models import Email, SubscriptionCategory

# @receiver(pre_save, sender=Email)
# # def migrate_unsubscriptions(sender, instance, raw, using, **kwargs):
# #     if instance and instance.id:
# #         old_instance = Email.objects.get(pk=instance.pk)

# #         if old_instance.subscription_category is None and instance.subscription_category is not None:
# #             instance.subscription_category.unsubscriptions.add(*instance.unsubscriptions.all())
