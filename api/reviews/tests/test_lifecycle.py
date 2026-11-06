from datetime import timedelta

import pytest

from reviews.models import FailureReason, ReviewStatus
from reviews.services.lifecycle import add_finding, complete, fail_ai_error
from reviews.services.plan import get_plan
from reviews.services.reads import get_review
from reviews.services.request import request_review
from reviews.tests.helpers import T0, document, lawyer

pytestmark = pytest.mark.usefixtures("seeded")


def after(seconds: float):
    return T0 + timedelta(seconds=seconds)


@pytest.fixture
def review():
    return request_review(document("nda"), lawyer("chiara"), T0)


@pytest.fixture
def samples():
    return list(document("nda").sample_findings.all())


def test_findings_are_stored_in_arrival_order_with_their_fields(review, samples):
    for seq, sample in enumerate(samples):
        assert add_finding(review.id, seq, sample, after(5 + seq))

    stored = list(review.findings.values("seq", "clause", "title", "severity", "excerpt", "explanation"))
    assert stored == [
        {
            "seq": seq,
            "clause": sample.clause,
            "title": sample.title,
            "severity": sample.severity,
            "excerpt": sample.excerpt,
            "explanation": sample.explanation,
        }
        for seq, sample in enumerate(samples)
    ]


def test_late_completion_is_ignored(review, samples):
    assert not add_finding(review.id, 0, samples[0], after(95))
    assert not complete(review.id, after(95))

    review = get_review(review.id, after(95))
    assert (review.status, review.failure_reason) == (ReviewStatus.FAILED, FailureReason.TIMED_OUT)
    assert review.findings.count() == 0
    plan = get_plan(after(95))
    assert (plan.completed, plan.available) == (0, 10)


def test_completion_at_exactly_60_seconds_fails(review):
    assert not complete(review.id, after(60))

    review = get_review(review.id, after(60))
    assert (review.status, review.failure_reason) == (ReviewStatus.FAILED, FailureReason.TIMED_OUT)


def test_completion_just_before_the_deadline_completes(review):
    assert complete(review.id, after(59.999))

    review = get_review(review.id, after(59.999))
    assert review.status == ReviewStatus.COMPLETED
    assert review.finished_at == after(59.999)
    assert get_plan(after(59.999)).completed == 1


def test_ai_error_fails_the_review_and_keeps_its_findings_stored(review, samples):
    add_finding(review.id, 0, samples[0], after(5))

    assert fail_ai_error(review.id, after(10))

    review.refresh_from_db()
    assert (review.status, review.failure_reason) == (ReviewStatus.FAILED, FailureReason.AI_ERROR)
    assert review.finished_at == after(10)
    assert review.findings.count() == 1


@pytest.mark.parametrize(
    "end", [complete, fail_ai_error], ids=["after completion", "after AI error"]
)
def test_a_finished_review_never_changes_again(review, samples, end):
    end(review.id, after(10))
    review.refresh_from_db()
    before = (review.status, review.failure_reason, review.finished_at)

    assert not add_finding(review.id, 0, samples[0], after(11))
    assert not complete(review.id, after(12))
    assert not fail_ai_error(review.id, after(13))

    review.refresh_from_db()
    assert (review.status, review.failure_reason, review.finished_at) == before
    assert review.findings.count() == 0


def test_a_timed_out_review_never_changes_again(review, samples):
    get_review(review.id, after(60))

    assert not add_finding(review.id, 0, samples[0], after(30))
    assert not complete(review.id, after(30))
    assert not fail_ai_error(review.id, after(30))

    review.refresh_from_db()
    assert (review.status, review.failure_reason) == (ReviewStatus.FAILED, FailureReason.TIMED_OUT)
