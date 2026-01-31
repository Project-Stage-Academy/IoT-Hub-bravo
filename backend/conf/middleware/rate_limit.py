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

class ClientIPResolver:

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

"""
RateLimiter is a class that checks if a request is limited.
"""

class RateLimiter:

    @staticmethod
    def is_limited(key, limit, window):
        try:
            current = cache.incr(key)

        except ValueError:
            created = cache.add(key, 1, window)
            current = 1 if created else cache.incr(key)

        except Exception as e:
            logger.exception("Rate limit cache error")
            return False

        return current > limit
            
"""
RateLimitResponseFactory is a class that builds the response for a rate limit exceeded.
"""

class RateLimitResponseFactory:

    @staticmethod
    def build(window):

        cfg = getattr(settings, "RATE_LIMIT_RESPONSE", {})

        return JsonResponse(
            {
                "code": cfg.get("code", 429),
                "message": cfg.get("message", "Too many requests"),
                "retry_after": window,
            },
            status=429,
            headers={"Retry-After": str(window)},
        )


"""
RateLimitRuleResolver is a class that resolves the rate limit rule for a given path.
"""

class RateLimitRuleResolver:

    @staticmethod
    def resolve(path):

        rule = EXACT_RULES.get(path)
        if rule:
            return rule

        for prefix, rule in PREFIX_RULES:
            if path.startswith(prefix):
                return rule

        return None


"""
RateLimitMiddleware is a class that is the main middleware for rate limiting.
"""

class RateLimitMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if not getattr(settings, "RATE_LIMIT_ENABLED", False):
            return None

        rule = RateLimitRuleResolver.resolve(request.path)
        if not rule:
            return None

        identifier = self._get_identifier(request)

        key = f"rl:{request.path}:{request.method}:{identifier}"

        if RateLimiter.is_limited(key, rule["limit"], rule["window"]):
            return RateLimitResponseFactory.build(rule["window"])

        return None

    def _get_identifier(self, request):
        if request.user.is_authenticated:
            return request.user.id
        ip = ClientIpResolver.get_ip(request)
        return f"ip:{ip}"