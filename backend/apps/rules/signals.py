from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from apps.rules.models.rule import Rule
from apps.common.redis_client import get_redis_client
import logging
from django.core.cache import caches

logger = logging.getLogger(__name__)


@receiver([post_save, post_delete], sender=Rule)
def invalidate_rule_cache(sender, instance, **kwargs):
    """
    """
    cache_rule = caches["rules"]
    

    device_metric = instance.device_metric
    if device_metric:

        cache_key = f"{device_metric.device.serial_id}:{device_metric.metric.metric_type}"
        
        cache_rule.delete(cache_key)
        logger.info(f"Cache invalidated for key: {cache_key} due to rule update/deletion.")