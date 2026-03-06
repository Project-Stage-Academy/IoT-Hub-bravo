from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .services import UserService
from apps.common.utils.views_utils import parse_json_body


@csrf_exempt
def login(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    data, error_response = parse_json_body(request.body)
    if error_response:
        return error_response

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
