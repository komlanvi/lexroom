"""HTTP only: translate requests into service calls and service errors into status codes."""

from uuid import UUID

from django.http import Http404
from ninja import Router, Status

from config.errors import ApiError
from reviews import clock
from reviews.models import Review
from reviews.schemas import DocumentOut, PlanOut, ReviewOut, ReviewSummaryOut
from reviews.services import reads
from reviews.services.plan import get_plan
from reviews.services.request import PlanExhausted, ReviewInProgress, request_review
from workspace.models import Document, Lawyer

router = Router()


@router.get("/plan", response=PlanOut)
def plan(request):
    return get_plan(clock.clock.now())


@router.get("/documents", response=list[DocumentOut])
def list_documents(request):
    return reads.list_documents(clock.clock.now())


@router.get("/documents/{document_id}", response=DocumentOut)
def get_document(request, document_id: UUID):
    try:
        return reads.get_document(document_id, clock.clock.now())
    except Document.DoesNotExist:
        raise Http404 from None


@router.post("/documents/{document_id}/reviews", response={201: ReviewOut})
def create_review(request, document_id: UUID):
    lawyer = _lawyer_from_header(request)
    document = Document.objects.filter(id=document_id).first()
    if document is None:
        raise Http404
    now = clock.clock.now()
    try:
        review = request_review(document, lawyer, now)
    except ReviewInProgress as error:
        raise ApiError(
            409,
            "REVIEW_IN_PROGRESS",
            "A review of this document is already in progress.",
            {"review": ReviewSummaryOut.from_orm(error.review).model_dump(mode="json")},
        ) from None
    except PlanExhausted as error:
        raise ApiError(
            409,
            "PLAN_EXHAUSTED",
            "This month's plan is used up.",
            {"resets_at": error.plan.resets_at, "completed": error.plan.completed, "running": error.plan.running},
        ) from None
    review.server_now = now
    return Status(201, review)


@router.get("/reviews/{review_id}", response=ReviewOut)
def get_review(request, review_id: UUID):
    now = clock.clock.now()
    try:
        review = reads.get_review(review_id, now)
    except Review.DoesNotExist:
        raise Http404 from None
    review.server_now = now
    return review


def _lawyer_from_header(request) -> Lawyer:
    """BR-14: every mutating call names a known lawyer. This identifies; it does not authenticate."""
    try:
        lawyer_id = UUID(request.headers.get("X-Lawyer-Id", ""))
        return Lawyer.objects.get(id=lawyer_id)
    except (ValueError, Lawyer.DoesNotExist):
        raise ApiError(400, "UNKNOWN_LAWYER", "Choose who you are before requesting a review.") from None
