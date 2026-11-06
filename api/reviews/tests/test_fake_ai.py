import random
from collections import Counter
from datetime import timedelta

import pytest

from reviews.fake_ai import Outcome, Script, run, write_script
from reviews.models import FailureReason, ReviewStatus
from reviews.services.lifecycle import fail_ai_error
from reviews.services.plan import get_plan
from reviews.services.reads import get_review
from reviews.services.request import request_review
from reviews.tests.helpers import document, lawyer

DRAWS = 10_000


def scripts(finding_count=3, seed=42):
    rng = random.Random(seed)
    return [write_script(finding_count, rng) for _ in range(DRAWS)]


# The script: what a run will do.


def test_outcomes_follow_the_brief_rates():
    counts = Counter(script.outcome for script in scripts())

    assert counts[Outcome.AI_ERROR] / DRAWS == pytest.approx(0.20, abs=0.02)
    assert counts[Outcome.SLOW] / DRAWS == pytest.approx(0.10, abs=0.02)
    assert counts[Outcome.COMPLETED] / DRAWS == pytest.approx(0.70, abs=0.02)


def test_a_completed_run_sends_every_finding_within_5_to_30_seconds():
    for script in scripts():
        if script.outcome == Outcome.COMPLETED:
            assert 5 <= script.end_time <= 30
            assert len(script.finding_times) == 3
            assert script.finding_times == sorted(script.finding_times)
            assert all(0 <= at <= script.end_time for at in script.finding_times)


def test_a_slow_run_lasts_60_to_120_seconds_so_it_always_misses_the_deadline():
    for script in scripts():
        if script.outcome == Outcome.SLOW:
            assert 60 <= script.end_time <= 120
            assert len(script.finding_times) == 3
            assert all(0 <= at <= script.end_time for at in script.finding_times)


def test_an_error_run_fails_within_5_to_30_seconds_after_0_to_all_findings():
    errors = [script for script in scripts() if script.outcome == Outcome.AI_ERROR]

    assert all(5 <= script.end_time <= 30 for script in errors)
    assert all(at <= script.end_time for script in errors for at in script.finding_times)
    assert {len(script.finding_times) for script in errors} == {0, 1, 2, 3}


def test_the_same_seed_writes_the_same_scripts():
    assert scripts(seed=7)[:50] == scripts(seed=7)[:50]


# The run: playing a script against the database.


@pytest.fixture
def clock(fake_clock):
    return fake_clock


@pytest.fixture
def sleep(clock):
    return lambda seconds: clock.advance(seconds=seconds)


def start_review(clock, document_name="nda"):
    return request_review(document(document_name), lawyer("chiara"), clock.now())


def statuses(review):
    review = get_review(review.id, review.requested_at + timedelta(minutes=10))
    return review.status, review.failure_reason


@pytest.mark.usefixtures("seeded")
def test_completed_run_stores_every_finding_then_completes(clock, sleep):
    review = start_review(clock)

    run(review.id, Script(Outcome.COMPLETED, [2.0, 4.5, 9.0], 12.0), clock, sleep)

    assert statuses(review) == (ReviewStatus.COMPLETED, None)
    assert [f.title for f in review.findings.all()] == [s.title for s in document("nda").sample_findings.all()]
    assert [f.received_at - review.requested_at for f in review.findings.all()] == [
        timedelta(seconds=2), timedelta(seconds=4.5), timedelta(seconds=9)
    ]
    review.refresh_from_db()
    assert review.finished_at == review.requested_at + timedelta(seconds=12)


@pytest.mark.usefixtures("seeded")
@pytest.mark.parametrize("sent", [0, 2], ids=["error before any finding", "error after 2 findings"])
def test_error_run_fails_with_an_ai_error_after_its_findings(clock, sleep, sent):
    review = start_review(clock)

    run(review.id, Script(Outcome.AI_ERROR, [3.0, 6.0][:sent], 8.0), clock, sleep)

    assert statuses(review) == (ReviewStatus.FAILED, FailureReason.AI_ERROR)
    assert review.findings.count() == sent
    assert get_plan(clock.now()).completed == 0


@pytest.mark.usefixtures("seeded")
def test_slow_run_times_out_never_counts_and_stops_at_the_deadline(clock, sleep):
    review = start_review(clock)

    run(review.id, Script(Outcome.SLOW, [20.0, 70.0, 100.0], 110.0), clock, sleep)

    assert statuses(review) == (ReviewStatus.FAILED, FailureReason.TIMED_OUT)
    assert review.findings.count() == 1
    assert clock.now() == review.requested_at + timedelta(seconds=70), "stopped at the first rejected event"
    assert get_plan(clock.now()).completed == 0


@pytest.mark.usefixtures("seeded")
def test_document_without_findings_completes_with_none(clock, sleep):
    review = start_review(clock, "consulting")

    run(review.id, Script(Outcome.COMPLETED, [], 6.0), clock, sleep)

    assert statuses(review) == (ReviewStatus.COMPLETED, None)
    assert review.findings.count() == 0


@pytest.mark.usefixtures("seeded")
def test_run_stops_as_soon_as_the_review_has_ended(clock, sleep):
    review = start_review(clock)
    fail_ai_error(review.id, clock.now())

    run(review.id, Script(Outcome.COMPLETED, [2.0, 4.0, 6.0], 10.0), clock, sleep)

    assert review.findings.count() == 0
    assert clock.now() == review.requested_at + timedelta(seconds=2)
