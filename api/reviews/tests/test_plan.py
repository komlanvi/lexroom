from datetime import UTC, datetime, timedelta

import pytest

from reviews.models import FailureReason, ReviewStatus
from reviews.services.lifecycle import complete, fail_ai_error
from reviews.services.plan import get_plan, plan_month
from reviews.services.request import request_review
from reviews.tests.helpers import ROME, T0, document, given_completed, given_review, lawyer


@pytest.mark.parametrize(
    ("now", "start", "end"),
    [
        pytest.param(
            datetime(2026, 11, 6, 10, 0, tzinfo=UTC),
            datetime(2026, 11, 1, tzinfo=ROME),
            datetime(2026, 12, 1, tzinfo=ROME),
            id="mid-month",
        ),
        pytest.param(
            datetime(2026, 10, 31, 23, 0, tzinfo=UTC),
            datetime(2026, 11, 1, tzinfo=ROME),
            datetime(2026, 12, 1, tzinfo=ROME),
            id="already November in Rome, still October in UTC",
        ),
        pytest.param(
            datetime(2026, 10, 31, 22, 59, 59, 999999, tzinfo=UTC),
            datetime(2026, 10, 1, tzinfo=ROME),
            datetime(2026, 11, 1, tzinfo=ROME),
            id="last instant of October in Rome",
        ),
        pytest.param(
            datetime(2026, 12, 31, 23, 30, tzinfo=UTC),
            datetime(2027, 1, 1, tzinfo=ROME),
            datetime(2027, 2, 1, tzinfo=ROME),
            id="new year in Rome",
        ),
        pytest.param(
            datetime(2026, 12, 15, 12, 0, tzinfo=UTC),
            datetime(2026, 12, 1, tzinfo=ROME),
            datetime(2027, 1, 1, tzinfo=ROME),
            id="December resets in January",
        ),
        pytest.param(
            datetime(2027, 3, 15, 12, 0, tzinfo=UTC),
            datetime(2027, 3, 1, tzinfo=ROME),
            datetime(2027, 4, 1, tzinfo=ROME),
            id="month with a daylight saving change",
        ),
    ],
)
def test_plan_month_is_the_rome_calendar_month(now, start, end):
    assert plan_month(now) == (start, end)


def test_daylight_saving_month_resets_at_rome_midnight():
    _, end = plan_month(datetime(2027, 3, 15, 12, 0, tzinfo=UTC))

    assert end.astimezone(UTC) == datetime(2027, 3, 31, 22, 0, tzinfo=UTC)


def test_plan_is_fully_available_without_reviews(db):
    plan = get_plan(T0)

    assert (plan.limit, plan.completed, plan.running, plan.available) == (10, 0, 0, 10)
    assert plan.period == "2026-11"
    assert plan.resets_at == datetime(2026, 12, 1, tzinfo=ROME)


def test_plan_endpoint_uses_the_application_clock(client, db, fake_clock):
    fake_clock.advance(days=100)  # 14 Feb 2027

    response = client.get("/api/plan")

    assert response.status_code == 200
    body = response.json()
    assert datetime.fromisoformat(body.pop("resets_at")) == datetime(2027, 2, 28, 23, 0, tzinfo=UTC)
    assert body == {"limit": 10, "completed": 0, "running": 0, "available": 10, "period": "2027-02"}


# Acceptance scenarios, feature "Plan".


def test_successful_review_consumes_one_slot(seeded):
    given_completed(3)

    review = request_review(document("nda"), lawyer("chiara"), T0)
    assert get_plan(T0).available == 6
    complete(review.id, T0 + timedelta(seconds=12))

    plan = get_plan(T0 + timedelta(seconds=12))
    assert (plan.completed, plan.running, plan.available) == (4, 0, 6)


def test_failed_review_does_not_consume(seeded):
    given_completed(3)

    review = request_review(document("nda"), lawyer("chiara"), T0)
    fail_ai_error(review.id, T0 + timedelta(seconds=8))

    plan = get_plan(T0 + timedelta(seconds=8))
    assert (plan.completed, plan.running, plan.available) == (3, 0, 7)


def test_running_reviews_reserve_slots(seeded):
    given_completed(9)

    request_review(document("nda"), lawyer("chiara"), T0)

    plan = get_plan(T0 + timedelta(seconds=1))
    assert (plan.completed, plan.running, plan.available) == (9, 1, 0)


def test_reservation_released_on_failure(seeded):
    given_completed(9)
    given_review("nda", T0, status=ReviewStatus.RUNNING)

    assert get_plan(T0 + timedelta(seconds=59)).available == 0
    assert get_plan(T0 + timedelta(seconds=60)).available == 1


def test_month_boundary_counts_in_the_month_of_the_request(seeded):
    requested_at = datetime(2026, 11, 30, 23, 59, 50, tzinfo=ROME)
    completed_at = datetime(2026, 12, 1, 0, 0, 5, tzinfo=ROME)

    review = request_review(document("nda"), lawyer("chiara"), requested_at)
    assert complete(review.id, completed_at)

    assert get_plan(requested_at).completed == 1
    december = get_plan(completed_at)
    assert (december.period, december.completed, december.available) == ("2026-12", 0, 10)


def test_review_running_at_midnight_does_not_reserve_a_slot_in_the_new_month(seeded):
    given_completed(9, requested_at=datetime(2026, 11, 20, 9, 0, tzinfo=ROME))
    given_review("nda", datetime(2026, 11, 30, 23, 59, 30, tzinfo=ROME), status=ReviewStatus.RUNNING)

    december = get_plan(datetime(2026, 12, 1, 0, 0, 0, tzinfo=ROME))

    assert (december.completed, december.running, december.available) == (0, 0, 10)


def test_reviews_failed_for_any_reason_never_count(seeded):
    given_review("nda", T0 - timedelta(hours=2), ReviewStatus.FAILED, FailureReason.AI_ERROR)
    given_review("nda", T0 - timedelta(hours=1), ReviewStatus.FAILED, FailureReason.TIMED_OUT)

    assert get_plan(T0).available == 10


def test_reviews_of_previous_months_never_count(seeded):
    given_completed(10, requested_at=datetime(2026, 10, 31, 23, 59, 59, tzinfo=ROME))

    assert get_plan(datetime(2026, 11, 1, 0, 0, 0, tzinfo=ROME)).available == 10
