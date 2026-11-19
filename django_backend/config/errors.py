from django.http import JsonResponse
from rest_framework import exceptions, status
from rest_framework.views import exception_handler as drf_exception_handler


class Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Conflict."
    default_code = "conflict"


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        if isinstance(exc, exceptions.ValidationError):
            response.status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        elif isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
            response.status_code = status.HTTP_401_UNAUTHORIZED
    return response


def not_found(request, exception):
    return JsonResponse({"detail": "Not found."}, status=404)
