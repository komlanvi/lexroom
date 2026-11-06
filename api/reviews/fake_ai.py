"""A stand-in for the AI reviewer, behaving as the brief describes.

About 1 run in 5 fails with an error (after 0 to all findings), about 1 in 10 is slow (60 to 120 s,
so it always misses the deadline), and the rest stream all findings over 5 to 30 s, then complete.
"""

import logging
import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from django.db import connection

from reviews import clock as clock_module
from reviews.clock import Clock
from reviews.models import Review
from reviews.services.lifecycle import add_finding, complete, fail_ai_error

logger = logging.getLogger(__name__)

ERROR_RATE = 0.2
SLOW_RATE = 0.1


class Outcome(StrEnum):
    COMPLETED = "completed"
    AI_ERROR = "ai_error"
    SLOW = "slow"


@dataclass(frozen=True)
class Script:
    """What one run will do: send a finding at each `finding_times` (seconds after the request),
    then complete, or fail if the outcome is AI_ERROR, at `end_time`."""

    outcome: Outcome
    finding_times: list[float]
    end_time: float


def write_script(finding_count: int, rng: random.Random) -> Script:
    draw = rng.random()
    if draw < ERROR_RATE:
        end_time = rng.uniform(5, 30)
        sent = rng.randint(0, finding_count)
        return Script(Outcome.AI_ERROR, _spread(sent, end_time, rng), end_time)
    if draw < ERROR_RATE + SLOW_RATE:
        end_time = rng.uniform(60, 120)
        return Script(Outcome.SLOW, _spread(finding_count, end_time, rng), end_time)
    end_time = rng.uniform(5, 30)
    return Script(Outcome.COMPLETED, _spread(finding_count, end_time, rng), end_time)


def _spread(count: int, duration: float, rng: random.Random) -> list[float]:
    return sorted(rng.uniform(0, duration) for _ in range(count))


def run(review_id: UUID, script: Script, clock: Clock, sleep: Callable[[float], None]) -> None:
    """Play the script. Stops at the first event the review no longer accepts (failed or past its deadline)."""
    review = Review.objects.get(id=review_id)
    samples = list(review.document.sample_findings.all())

    def wait_until(seconds_after_request: float) -> datetime:
        target = review.requested_at + timedelta(seconds=seconds_after_request)
        sleep(max(0.0, (target - clock.now()).total_seconds()))
        return clock.now()

    for seq, (at, sample) in enumerate(zip(script.finding_times, samples, strict=False)):
        if not add_finding(review_id, seq, sample, wait_until(at)):
            return

    now = wait_until(script.end_time)
    if script.outcome == Outcome.AI_ERROR:
        fail_ai_error(review_id, now)
    else:
        complete(review_id, now)


def start(review_id: UUID) -> None:
    """Run the fake AI for this review in a background thread."""
    threading.Thread(target=_run_in_thread, args=(review_id,), daemon=True).start()


def _run_in_thread(review_id: UUID) -> None:
    try:
        finding_count = Review.objects.get(id=review_id).document.sample_findings.count()
        script = write_script(finding_count, random.Random())
        logger.info("Fake AI for review %s: %s, ends after %.1f s.", review_id, script.outcome, script.end_time)
        run(review_id, script, clock_module.clock, time.sleep)
    except Exception:
        # The review then simply times out at its deadline and frees its plan slot.
        logger.exception("Fake AI crashed for review %s.", review_id)
    finally:
        connection.close()
