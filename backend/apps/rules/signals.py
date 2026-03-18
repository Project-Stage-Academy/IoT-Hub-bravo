import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import caches

from apps.rules.models.rule import Rule

logger = logging.getLogger(__name__)


@receiver([post_save, post_delete], sender=Rule)
def invalidate_rule_cache(sender, instance, **kwargs):
    logger.debug(f"!!! SIGNAL TRIGGERED for Rule: {instance.id} !!!")

    try:
        cache_rule = caches["rules"]
        device_metric = instance.device_metric

        if device_metric:
            serial_id = device_metric.device.serial_id
            device_metric_id = device_metric.id

            cache_key = f"{serial_id}:{device_metric_id}"

            cache_rule.delete(cache_key)
            logger.debug(f"!!! CACHE DELETED: {cache_key} !!!")
            logger.debug(f"Cache invalidated for key: {cache_key}")

    except Exception as e:
        logger.exception(f"!!! ERROR IN SIGNAL: {e} !!!")
