# Create your views here.

import json
from .models import User
from .services import UserService
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def login(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    username = data.get("username")
    password = data.get("password")

    if not username or not isinstance(username, str):
        return JsonResponse({"error": "Username is required"}, status=400)
    if not password or not isinstance(password, str):
        return JsonResponse({"error": "Password is required"}, status=400)

    try:
        token_data = UserService.get_access_token(username=username, password=password)
    except RuntimeError:
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse(token_data)
