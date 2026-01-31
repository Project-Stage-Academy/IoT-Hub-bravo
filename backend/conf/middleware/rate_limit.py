from django.conf import settings
import re
import logging

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