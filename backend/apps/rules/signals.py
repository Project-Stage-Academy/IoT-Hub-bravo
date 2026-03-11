from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from apps.rules.models.rule import Rule
import logging
from django.core.cache import caches

logger = logging.getLogger(__name__)

@receiver([post_save, pre_delete], sender=Rule)
def invalidate_rule_cache(sender, instance, **kwargs):
    print(f"!!! SIGNAL TRIGGERED for Rule: {instance.id} !!!") 
    
    try:
        cache_rule = caches["rules"]
        device_metric = instance.device_metric
        
        if device_metric:
            serial_id = device_metric.device.serial_id
            metric_type = device_metric.metric.metric_type
            
            cache_key = f"{serial_id}:{metric_type}"
            
            cache_rule.delete(cache_key)
            print(f"!!! CACHE DELETED: {cache_key} !!!")
            logger.info(f"Cache invalidated for key: {cache_key}")
            
    except Exception as e:
        print(f"!!! ERROR IN SIGNAL: {e} !!!")