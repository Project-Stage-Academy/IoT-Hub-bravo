from django.http import HttpResponse
import logging
from django.http import HttpResponseServerError
from prometheus_client import Counter

logger = logging.getLogger("rules") # logger.setLevel(logging.INFO) - is default
my_metric = Counter('my_metric_total', 'Description')

def rules_index(request):
    """Home page for rules/"""
    logger.warning("Platform is running at risk", extra={"context": {"user_id": 12, "smt": "1123"}})
    # raise PermissionDenied("You can't access this page")
    # raise Http404("Page not found")
    # value = "E41" 
    # logger.info("some info")
    # logger.critical("something really bad", extra={"custom_field": "some value", "error_code": value})

    my_metric.inc()
    return HttpResponseServerError("grafana test")    
    # return HttpResponse("app is working 12312321")