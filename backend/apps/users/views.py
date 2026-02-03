# Create your views here.

import json
from .models import User
from .services import UserService
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def login(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"},status=405)
    try:
        return json.loads(request.body), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON"}, status=400)

    username = data_from_json.get("username")
    password = data_from_json.get("password")
    if not username or not isinstance(username, str):
        return JsonResponse({"error": "Username is required"}, status=400)
    if not password or not isinstance(password, str):
        return JsonResponse({"error": "Password is required"}, status=400)
    try:
        token_data = UserService.get_access_token(username=username, password=password)
    except Exception:
        return JsonResponse({"error": "Invalid credentials"}, status=401)
    return JsonResponse(token_data)

