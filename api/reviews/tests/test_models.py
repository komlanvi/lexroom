from datetime import UTC, datetime, timedelta

import pytest
from django.db import IntegrityError, transaction

from reviews.models import Finding, Review
from workspace.models import Document

NOW = datetime(2026, 11, 6, 10, 0, tzinfo=UTC)

pytestmark = pytest.mark.usefixtures("seeded")


def make_review(document=None, **fields):
    document = document or Document.objects.first()
    return Review.objects.create(
        document=document,
        requested_by=document.uploaded_by,
        requested_at=NOW,
        deadline_at=NOW + timedelta(seconds=60),
        **fields,
    )


def assert_rejected(create):
    with pytest.raises(IntegrityError), transaction.atomic():
        create()


def test_second_running_review_on_the_same_document_is_rejected():
    document = Document.objects.first()
    make_review(document)

    assert_rejected(lambda: make_review(document))


def test_running_reviews_on_different_documents_are_allowed():
    first, second = Document.objects.all()[:2]

    make_review(first)
    make_review(second)

    assert Review.objects.filter(status="running").count() == 2


@pytest.mark.parametrize(
    "finished", [{"status": "completed"}, {"status": "failed", "failure_reason": "timed_out"}]
)
def test_a_finished_review_does_not_block_a_new_running_one(finished):
    document = Document.objects.first()
    make_review(document, finished_at=NOW, **finished)

    make_review(document)

    assert document.reviews.count() == 2


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "cancelled"},
        {"status": "failed"},
        {"status": "failed", "failure_reason": "unknown"},
        {"status": "running", "failure_reason": "ai_error"},
        {"status": "completed", "failure_reason": "timed_out"},
    ],
    ids=["unknown status", "failed without reason", "unknown reason", "running with reason", "completed with reason"],
)
def test_invalid_status_and_failure_reason_combinations_are_rejected(fields):
    assert_rejected(lambda: make_review(**fields))


@pytest.mark.parametrize("reason", ["ai_error", "timed_out"])
def test_failed_review_accepts_each_failure_reason(reason):
    review = make_review(status="failed", failure_reason=reason, finished_at=NOW)

    assert review.failure_reason == reason


def test_finding_sequence_is_unique_per_review():
    review = make_review()
    finding = {"title": "t", "severity": "high", "explanation": "e", "received_at": NOW}
    Finding.objects.create(review=review, seq=0, **finding)

    assert_rejected(lambda: Finding.objects.create(review=review, seq=0, **finding))


def test_finding_keeps_null_clause_and_excerpt():
    review = make_review()

    finding = Finding.objects.create(
        review=review, seq=0, clause=None, excerpt=None, title="t", severity="low", explanation="e", received_at=NOW
    )

    finding.refresh_from_db()
    assert (finding.clause, finding.excerpt) == (None, None)
