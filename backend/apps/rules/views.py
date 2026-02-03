import logging
from django.http import JsonResponse

logger = logging.getLogger("rules")  # logger.setLevel(logging.INFO) - is default


def rules_index(request):
    """Home page for rules/"""
    logger.critical("Platform is running at risk", extra={"context": {"user_id": 12, "smt": "1123"}})

    return JsonResponse({"status": "ok", "message": "grafana test"})
