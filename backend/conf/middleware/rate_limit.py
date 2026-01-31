from django.conf import settings
import re
import logging

import ipaddress 
from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

"""
RATE_LIMIT_RULES is a dictionary of path patterns and their rate limit configurations.
"""

EXACT_RULES = {}
PREFIX_RULES = []

def _compile_rules():
    rules = getattr(settings, "RATE_LIMIT_RULES", {})

    for path, config in rules.items():
        if path.endswith('/'):
            PREFIX_RULES.append((path, config))
        else:
            EXACT_RULES[path] = config

    PREFIX_RULES.sort(key=lambda x: -len(x[0]))

_compile_rules()


"""
ClientIpResolver is a class that resolves the client IP address from the request.
"""

class ClientIpResolver:

    @staticmethod
    def get_ip(request):
        remote_addr = request.META.get('REMOTE_ADDR')

        if not remote_addr:
            return '127.0.0.1'

        if not ClientIPResolver._is_trusted_proxy(remote_addr):
            return remote_addr

        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')

        if not forwarded:
            return remote_addr

        ips = [ip.strip() for ip in forwarded.split(',')]

        for ip in reversed(ips):
            try:
                ipaddress.ip_address(ip)
                return ip
            except ValueError:
                continue

        return remote_addr

        @staticmethod
        def _is_trusted_proxy(ip):
            proxies = getattr(settings, "RATE_LIMIT_TRUSTED_PROXIES", [])

        try:
            remote_ip = ipaddress.ip_address(ip)

            for net in proxies:
                if remote_ip in ipaddress.ip_network(net):
                    return True

        except ValueError:
            pass

        return False
