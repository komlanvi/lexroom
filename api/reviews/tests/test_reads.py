from datetime import datetime, timedelta

import pytest

from reviews.models import FailureReason, ReviewStatus
from reviews.services.reads import current_result, get_document, get_review, latest_review, list_documents
from reviews.services.request import request_review
from reviews.tests.helpers import DOCUMENTS, ROME, T0, document, given_review, lawyer

pytestmark = pytest.mark.usefixtures("seeded")


def test_document_never_reviewed_has_no_latest_review_and_no_result():
    assert latest_review(document("nda")) is None
    assert current_result(document("nda")) is None


def test_previous_review_skips_failed_reviews():
    completed = given_review("lease_v2", datetime(2026, 11, 2, 14, 3, tzinfo=ROME))
    given_review("lease_v2", datetime(2026, 11, 4, 9, 0, tzinfo=ROME), ReviewStatus.FAILED, FailureReason.AI_ERROR)

    running = request_review(document("lease_v2"), lawyer("riccardo"), T0)

    assert latest_review(document("lease_v2")) == running
    assert current_result(document("lease_v2")) == completed


def test_latest_review_is_the_most_recent_request_whatever_its_status():
    given_review("loan", T0 - timedelta(days=2))
    failed = given_review("loan", T0 - timedelta(days=1), ReviewStatus.FAILED, FailureReason.TIMED_OUT)

    assert latest_review(document("loan")) == failed


def test_a_newer_completed_review_replaces_the_current_result():
    given_review("nda", T0 - timedelta(days=2))
    newer = given_review("nda", T0 - timedelta(days=1))

    assert current_result(document("nda")) == newer


def test_reviews_of_one_document_version_never_replace_another_version():
    v1_review = given_review("lease_v1", T0 - timedelta(days=1))
    v2_review = given_review("lease_v2", T0)

    assert current_result(document("lease_v1")) == v1_review
    assert current_result(document("lease_v2")) == v2_review


@pytest.mark.parametrize(
    "read",
    [
        lambda review, now: get_review(review.id, now),
        lambda review, now: get_document(review.document_id, now).latest_review,
        lambda review, now: next(d for d in list_documents(now) if d.id == review.document_id).latest_review,
    ],
    ids=["get_review", "get_document", "list_documents"],
)
def test_every_read_reports_an_overdue_review_as_timed_out(read):
    overdue = given_review("nda", T0 - timedelta(seconds=60), status=ReviewStatus.RUNNING)

    review = read(overdue, T0)

    assert (review.status, review.failure_reason) == (ReviewStatus.FAILED, FailureReason.TIMED_OUT)


def test_list_documents_attaches_each_documents_own_reviews():
    nda_review = given_review("nda", T0 - timedelta(days=1))

    documents = {str(d.id): d for d in list_documents(T0)}

    assert documents[DOCUMENTS["nda"]].latest_review == nda_review
    assert documents[DOCUMENTS["nda"]].current_result == nda_review
    others = [d for id_, d in documents.items() if id_ != DOCUMENTS["nda"]]
    assert all(d.latest_review is None and d.current_result is None for d in others)
