from datetime import datetime

from django.db.models import F

from reviews.models import FailureReason, Review, ReviewStatus


def expire_overdue(now: datetime) -> int:
    """BR-8: a running review past its deadline is failed/timed_out. Returns how many were expired."""
    return Review.objects.filter(status=ReviewStatus.RUNNING, deadline_at__lte=now).update(
        status=ReviewStatus.FAILED,
        failure_reason=FailureReason.TIMED_OUT,
        finished_at=F("deadline_at"),
    )
