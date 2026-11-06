from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction

from reviews.models import Review, ReviewStatus
from reviews.services.expiry import expire_overdue
from reviews.services.plan import Plan, get_plan
from workspace.models import Document, Lawyer


class ReviewInProgress(Exception):
    def __init__(self, review: Review):
        super().__init__(f"Review {review.id} is already running on this document.")
        self.review = review


class PlanExhausted(Exception):
    def __init__(self, plan: Plan):
        super().__init__("No review left in this month's plan.")
        self.plan = plan


def request_review(document: Document, lawyer: Lawyer, now: datetime) -> Review:
    """BR-3: accept a review only if the document has none running and the plan has a slot."""
    # SQLite runs this transaction in IMMEDIATE mode: the write lock is held from the start,
    # so concurrent requests are checked one after the other.
    # On PostgreSQL, lock a shared row here with select_for_update() to get the same guarantee.
    with transaction.atomic():
        expire_overdue(now)

        running = Review.objects.filter(document=document, status=ReviewStatus.RUNNING).first()
        if running is not None:
            raise ReviewInProgress(running)

        plan = get_plan(now)
        if plan.available < 1:
            raise PlanExhausted(plan)

        return Review.objects.create(
            document=document,
            requested_by=lawyer,
            requested_at=now,
            deadline_at=now + timedelta(seconds=settings.REVIEW_TIMEOUT_S),
        )
