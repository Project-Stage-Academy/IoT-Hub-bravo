from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import ipaddress

class RateLimitMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not getattr(settings, 'RATE_LIMIT_ENABLED', False):
            return None

        rate_limit_config = getattr(settings, 'RATE_LIMIT_CONFIG', {})
        path = request.path
        method = request.method
        client_ip = self._get_client_ip(request)

        matching_pattern = []
        for pattern, config in rate_limit_config.items():
            if self._matches_pattern(path, pattern):
                is_exact = not pattern.endswith('/')
                matching_pattern.append((is_exact, pattern, config))
        
        if not matching_pattern:
            return None
        
        def specificity_key(x):
            is_exact, pattern, config = x
            return (not is_exact, -len(pattern))
        
        _, pattern, config = min(matching_pattern, key=specificity_key)
        limit = config.get('limit', 100)
        window = config.get('window', 60)
        key = f"ratelimit:{pattern}:{client_ip}:{method}"

        try:
            current = cache.incr(key)
        except ValueError:
            if not cache.add(key, 1, window):
                current = cache.incr(key)
            else:
                current = 1

        if current > limit:
            return JsonResponse(
                {
                    'code': 429,
                    'message': 'Rate limit exceeded',
                    'retry_after': window
                },
                status=429,
                headers={'Retry-After': str(window)}
            )

        return None

    def _get_client_ip(self, request):
        """
        Safely obtains the client IP, protecting against X-Forwarded-For spoofing. 
        Uses X-Forwarded-For only if REMOTE_ADDR is a trusted proxy.
        """
        remote_addr = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        trusted_proxies = getattr(settings, 'RATE_LIMIT_TRUSTED_PROXIES', [])
        
        is_trusted_proxy = False
        if trusted_proxies:
            try:
                remote_ip = ipaddress.ip_address(remote_addr)
                for proxy in trusted_proxies:
                    if remote_ip in ipaddress.ip_network(proxy, strict=False):
                        is_trusted_proxy = True
                        break
            except (ValueError, ipaddress.AddressValueError):
                pass
        
        if is_trusted_proxy:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
                try:
                    ipaddress.ip_address(ip)
                    return ip
                except (ValueError, ipaddress.AddressValueError):
                    pass
        
        return remote_addr

    def _matches_pattern(self, path, pattern):
        if pattern.endswith('/'):
            return path.startswith(pattern)
        return path == pattern

