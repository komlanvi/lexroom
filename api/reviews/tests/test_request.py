from datetime import datetime, timedelta

import pytest

from reviews.models import FailureReason, Review, ReviewStatus
from reviews.services.request import PlanExhausted, ReviewInProgress, request_review
from reviews.tests.helpers import ROME, T0, document, given_completed, given_review, lawyer

pytestmark = pytest.mark.usefixtures("seeded")


def test_accepted_request_creates_a_running_review_with_a_60_second_deadline():
    review = request_review(document("nda"), lawyer("sofia"), T0)

    review.refresh_from_db()
    assert review.status == ReviewStatus.RUNNING
    assert review.requested_by == lawyer("sofia")
    assert review.requested_at == T0
    assert review.deadline_at == T0 + timedelta(seconds=60)
    assert (review.failure_reason, review.finished_at) == (None, None)


def test_running_reviews_block_the_last_slot_and_the_request_is_not_saved():
    given_completed(9)
    request_review(document("nda"), lawyer("chiara"), T0)

    with pytest.raises(PlanExhausted) as blocked:
        request_review(document("loan"), lawyer("riccardo"), T0 + timedelta(seconds=5))

    plan = blocked.value.plan
    assert (plan.completed, plan.running, plan.available) == (9, 1, 0)
    assert not Review.objects.filter(document=document("loan")).exists()


def test_strict_block_when_the_plan_is_used_up():
    given_completed(10)

    with pytest.raises(PlanExhausted) as blocked:
        request_review(document("nda"), lawyer("chiara"), T0)

    assert blocked.value.plan.resets_at == datetime(2026, 12, 1, 0, 0, tzinfo=ROME)
    assert Review.objects.count() == 10


def test_second_request_on_a_running_document_returns_the_running_review():
    running = request_review(document("saas"), lawyer("chiara"), T0)

    with pytest.raises(ReviewInProgress) as blocked:
        request_review(document("saas"), lawyer("sofia"), T0 + timedelta(seconds=1))

    assert blocked.value.review == running
    assert Review.objects.count() == 1


def test_document_in_progress_is_reported_before_an_exhausted_plan():
    given_completed(9)
    request_review(document("saas"), lawyer("chiara"), T0)

    with pytest.raises(ReviewInProgress):
        request_review(document("saas"), lawyer("sofia"), T0 + timedelta(seconds=1))


def test_stale_running_row_does_not_block():
    stale = given_review("nda", T0 - timedelta(seconds=90), status=ReviewStatus.RUNNING)

    new = request_review(document("nda"), lawyer("sofia"), T0)

    stale.refresh_from_db()
    assert (stale.status, stale.failure_reason) == (ReviewStatus.FAILED, FailureReason.TIMED_OUT)
    assert stale.finished_at == stale.deadline_at
    assert new.status == ReviewStatus.RUNNING


def test_stale_running_row_does_not_hold_the_last_slot():
    given_completed(9)
    given_review("loan", T0 - timedelta(seconds=60), status=ReviewStatus.RUNNING)

    review = request_review(document("nda"), lawyer("sofia"), T0)

    assert review.status == ReviewStatus.RUNNING


def test_retry_is_a_new_review():
    failed = given_review("loan", T0 - timedelta(minutes=5), ReviewStatus.FAILED, FailureReason.AI_ERROR)

    retry = request_review(document("loan"), lawyer("chiara"), T0)

    assert retry.id != failed.id
    assert retry.deadline_at == T0 + timedelta(seconds=60)
    failed.refresh_from_db()
    assert (failed.status, failed.failure_reason) == (ReviewStatus.FAILED, FailureReason.AI_ERROR)


def test_a_completed_review_does_not_block_a_new_request():
    given_review("nda", T0 - timedelta(days=1))

    review = request_review(document("nda"), lawyer("riccardo"), T0)

    assert review.status == ReviewStatus.RUNNING
