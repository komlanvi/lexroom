"""Events from the AI. Each one is applied only while the review is running and before its deadline (BR-9)."""

import logging
from datetime import datetime
from uuid import UUID

from django.db import transaction

from reviews.models import FailureReason, Finding, Review, ReviewStatus
from workspace.models import SampleFinding

logger = logging.getLogger(__name__)


def _still_running(review_id: UUID, now: datetime):
    return Review.objects.filter(id=review_id, status=ReviewStatus.RUNNING, deadline_at__gt=now)


def add_finding(review_id: UUID, seq: int, sample: SampleFinding, now: datetime) -> bool:
    with transaction.atomic():
        if not _still_running(review_id, now).exists():
            logger.info("Dropped finding %s of review %s: review no longer running.", seq, review_id)
            return False
        Finding.objects.create(
            review_id=review_id,
            seq=seq,
            clause=sample.clause,
            title=sample.title,
            severity=sample.severity,
            excerpt=sample.excerpt,
            explanation=sample.explanation,
            received_at=now,
        )
        return True


def complete(review_id: UUID, now: datetime) -> bool:
    applied = _still_running(review_id, now).update(status=ReviewStatus.COMPLETED, finished_at=now)
    if not applied:
        logger.info("Dropped completion of review %s: review no longer running.", review_id)
    return bool(applied)


def fail_ai_error(review_id: UUID, now: datetime) -> bool:
    applied = _still_running(review_id, now).update(
        status=ReviewStatus.FAILED, failure_reason=FailureReason.AI_ERROR, finished_at=now
    )
    if not applied:
        logger.info("Dropped AI error of review %s: review no longer running.", review_id)
    return bool(applied)
