from django.http import Http404
from ninja import NinjaAPI
from ninja.errors import ValidationError

from config.errors import ApiError, error_response
from reviews.api import router as reviews_router
from workspace.api import router as workspace_router

api = NinjaAPI(title="Lexroom API", docs_url=None)
api.add_router("", workspace_router)
api.add_router("", reviews_router)


@api.exception_handler(ApiError)
def api_error(request, exc):
    return error_response(exc)


@api.exception_handler(Http404)
def not_found(request, exc):
    return error_response(ApiError(404, "NOT_FOUND", "Not found."))


@api.exception_handler(ValidationError)
def invalid_request(request, exc):
    return error_response(ApiError(422, "INVALID_REQUEST", "Invalid request.", {"errors": exc.errors}))
