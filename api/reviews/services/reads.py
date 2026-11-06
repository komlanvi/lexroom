"""Every read applies lazy expiry first (BR-8), so an overdue review is never reported as running."""

from datetime import datetime
from uuid import UUID

from reviews.models import Review, ReviewStatus
from reviews.services.expiry import expire_overdue
from workspace.models import Document


def get_review(review_id: UUID, now: datetime) -> Review:
    expire_overdue(now)
    return Review.objects.get(id=review_id)


def list_documents(now: datetime) -> list[Document]:
    """All documents, newest upload first, each with `latest_review` and `current_result` set."""
    expire_overdue(now)
    documents = list(Document.objects.select_related("superseded_by").order_by("-uploaded_at"))
    for document in documents:
        _attach_reviews(document)
    return documents


def get_document(document_id: UUID, now: datetime) -> Document:
    """One document with `latest_review` and `current_result` set."""
    expire_overdue(now)
    document = Document.objects.select_related("superseded_by").get(id=document_id)
    _attach_reviews(document)
    return document


def latest_review(document: Document) -> Review | None:
    """BR-19: the most recent request, whatever its status."""
    return document.reviews.order_by("-requested_at").first()


def current_result(document: Document) -> Review | None:
    """BR-18 / BR-19: the most recent completed review. Failed reviews are never a result.

    While a new review runs, this is the "previous result" shown as no longer current.
    """
    return document.reviews.filter(status=ReviewStatus.COMPLETED).order_by("-requested_at").first()


def _attach_reviews(document: Document) -> None:
    document.latest_review = latest_review(document)
    document.current_result = current_result(document)
