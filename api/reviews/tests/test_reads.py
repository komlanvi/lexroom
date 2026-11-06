from datetime import datetime, timedelta

import pytest

from reviews.models import FailureReason, ReviewStatus
from reviews.services.reads import current_result, latest_review
from reviews.services.request import request_review
from reviews.tests.helpers import ROME, T0, document, given_review, lawyer

pytestmark = pytest.mark.usefixtures("seeded")


def test_document_never_reviewed_has_no_latest_review_and_no_result():
    assert latest_review(document("nda"), T0) is None
    assert current_result(document("nda")) is None


def test_previous_review_skips_failed_reviews():
    completed = given_review("lease_v2", datetime(2026, 11, 2, 14, 3, tzinfo=ROME))
    given_review("lease_v2", datetime(2026, 11, 4, 9, 0, tzinfo=ROME), ReviewStatus.FAILED, FailureReason.AI_ERROR)

    running = request_review(document("lease_v2"), lawyer("riccardo"), T0)

    assert latest_review(document("lease_v2"), T0) == running
    assert current_result(document("lease_v2")) == completed


def test_latest_review_is_the_most_recent_request_whatever_its_status():
    given_review("loan", T0 - timedelta(days=2))
    failed = given_review("loan", T0 - timedelta(days=1), ReviewStatus.FAILED, FailureReason.TIMED_OUT)

    assert latest_review(document("loan"), T0) == failed


def test_a_newer_completed_review_replaces_the_current_result():
    given_review("nda", T0 - timedelta(days=2))
    newer = given_review("nda", T0 - timedelta(days=1))

    assert current_result(document("nda")) == newer


def test_reviews_of_one_document_version_never_replace_another_version():
    v1_review = given_review("lease_v1", T0 - timedelta(days=1))
    v2_review = given_review("lease_v2", T0)

    assert current_result(document("lease_v1")) == v1_review
    assert current_result(document("lease_v2")) == v2_review


def test_latest_review_reports_an_overdue_review_as_timed_out():
    given_review("nda", T0 - timedelta(seconds=61), status=ReviewStatus.RUNNING)

    review = latest_review(document("nda"), T0)

    assert (review.status, review.failure_reason) == (ReviewStatus.FAILED, FailureReason.TIMED_OUT)
