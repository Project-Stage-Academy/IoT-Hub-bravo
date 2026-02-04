from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response

class CustomLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 5
    max_limit = 100

    def get_paginated_response(self, data):
        return Response({
            "total": self.count,
            "limit": self.limit,
            "offset": self.offset,
            "items": data
        })
