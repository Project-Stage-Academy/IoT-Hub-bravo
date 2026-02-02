from django.http import HttpResponse
import logging
from django.http import HttpResponseServerError

logger = logging.getLogger("rules") # logger.setLevel(logging.INFO) - is default

def rules_index(request):
    """Home page for rules/"""
    logger.warning("Platform is running at risk", extra={"context": {"user_id": 12, "smt": "1123"}})

    return HttpResponseServerError("grafana test")