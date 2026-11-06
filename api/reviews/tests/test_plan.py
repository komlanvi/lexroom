from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from reviews.services.plan import get_plan, plan_month

ROME = ZoneInfo("Europe/Rome")


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
    plan = get_plan(datetime(2026, 11, 6, 10, 0, tzinfo=UTC))

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
