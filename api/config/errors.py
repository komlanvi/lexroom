from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}


def error_response(error: ApiError) -> JsonResponse:
    """Every API error has the same body: {code, message, details}."""
    return JsonResponse(
        {"code": error.code, "message": error.message, "details": error.details},
        status=error.status,
        encoder=DjangoJSONEncoder,
    )
