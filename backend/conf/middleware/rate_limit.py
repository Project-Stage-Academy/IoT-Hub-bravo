from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class RateLimitMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not getattr(settings, 'RATE_LIMIT_ENABLED', False):
            return None

        rate_limit_config = getattr(settings, 'RATE_LIMIT_CONFIG', {})
        path = request.path
        method = request.method
        client_ip = self._get_client_ip(request)

        for pattern, config in rate_limit_config.items():
            if self._matches_pattern(path, pattern):
                limit = config.get('limit', 100)
                window = config.get('window', 60)
                key = f"ratelimit:{pattern}:{client_ip}:{method}"

                current = cache.get(key, 0)
                if current >= limit:
                    return JsonResponse(
                        {
                            'code': 429,
                            'message': 'Rate limit exceeded',
                            'retry_after': window
                        },
                        status=429,
                        headers={'Retry-After': str(window)}
                    )

                cache.set(key, current + 1, window)
                return None

        return None

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
        return ip

    def _matches_pattern(self, path, pattern):
        if pattern.endswith('/'):
            return path.startswith(pattern)
        return path == pattern

