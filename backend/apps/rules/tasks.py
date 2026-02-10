from celery import shared_task
from celery.utils.log import get_task_logger

from apps.devices.models.telemetry import Telemetry
from apps.rules.services.rule_processor import RuleProcessor

logger_celery = get_task_logger(__name__)

@shared_task(name="check_system_status")
def check_system_status():
    """Test example"""
    logger_celery.info("--- CELERY BEAT IS WORKING: System status checked! ---")
    return "Success"

@shared_task(name="run_rule_processor")
def run_rule_processor(telemetry_id: int):
    """
    Celery task to run RuleProcessor asynchronously on the given telemetry
    """
    telemetry = Telemetry.objects.get(id=telemetry_id)
    RuleProcessor.run(telemetry)
    logger_celery.info("Rule processor")