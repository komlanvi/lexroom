from django.http import Http404
from ninja import NinjaAPI
from ninja.errors import ValidationError

from reviews.api import router as reviews_router
from workspace.api import router as workspace_router

api = NinjaAPI(title="Lexroom API", docs_url=None)
api.add_router("", workspace_router)
api.add_router("", reviews_router)


def error_response(request, status: int, code: str, message: str, details: dict | None = None):
    """Every API error has the same body: {code, message, details}."""
    return api.create_response(
        request, {"code": code, "message": message, "details": details or {}}, status=status
    )


@api.exception_handler(Http404)
def not_found(request, exc):
    return error_response(request, 404, "NOT_FOUND", "Not found.")


@api.exception_handler(ValidationError)
def invalid_request(request, exc):
    return error_response(request, 422, "INVALID_REQUEST", "Invalid request.", {"errors": exc.errors})
