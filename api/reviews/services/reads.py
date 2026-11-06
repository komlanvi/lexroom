"""Reads of a review's status apply lazy expiry first (BR-8), so an overdue review is never reported as running."""

from datetime import datetime
from uuid import UUID

from reviews.models import Review, ReviewStatus
from reviews.services.expiry import expire_overdue
from workspace.models import Document


def get_review(review_id: UUID, now: datetime) -> Review:
    expire_overdue(now)
    return Review.objects.get(id=review_id)


def latest_review(document: Document, now: datetime) -> Review | None:
    """BR-19: the most recent request, whatever its status."""
    expire_overdue(now)
    return document.reviews.order_by("-requested_at").first()


def current_result(document: Document) -> Review | None:
    """BR-18 / BR-19: the most recent completed review. Failed reviews are never a result.

    While a new review runs, this is the "previous result" shown as no longer current.
    """
    return document.reviews.filter(status=ReviewStatus.COMPLETED).order_by("-requested_at").first()
