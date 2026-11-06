"""Simultaneous requests from separate threads, each with its own database connection."""

import io
import threading

import pytest
from django.core.management import call_command
from django.db import connection

from reviews.models import Review
from reviews.services.request import PlanExhausted, ReviewInProgress, request_review
from reviews.tests.helpers import T0, document, given_completed, lawyer

REQUESTS = 5


@pytest.fixture
def seeded_transactional(transactional_db):
    call_command("seed", stdout=io.StringIO())


def run_at_the_same_time(calls):
    barrier = threading.Barrier(len(calls))
    outcomes = [None] * len(calls)

    def run(index, call):
        try:
            barrier.wait()
            outcomes[index] = call()
        except Exception as error:
            outcomes[index] = error
        finally:
            connection.close()

    threads = [threading.Thread(target=run, args=(i, call)) for i, call in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return outcomes


def kinds(outcomes):
    return sorted(type(outcome).__name__ for outcome in outcomes)


@pytest.mark.parametrize("attempt", range(5))
def test_concurrent_requests_on_the_same_document_create_exactly_one_review(seeded_transactional, attempt):
    saas = document("saas")
    lawyers = [lawyer("chiara"), lawyer("sofia"), lawyer("riccardo")]

    outcomes = run_at_the_same_time(
        [lambda i=i: request_review(saas, lawyers[i % 3], T0) for i in range(REQUESTS)]
    )

    assert kinds(outcomes) == ["Review"] + [ReviewInProgress.__name__] * (REQUESTS - 1)
    assert Review.objects.count() == 1


@pytest.mark.parametrize("attempt", range(5))
def test_concurrent_requests_for_the_last_slot_accept_exactly_one(seeded_transactional, attempt):
    given_completed(9)
    documents = [document(name) for name in ("nda", "saas", "supply", "loan", "lease_v2")]

    outcomes = run_at_the_same_time(
        [lambda d=d: request_review(d, lawyer("chiara"), T0) for d in documents]
    )

    assert kinds(outcomes) == [PlanExhausted.__name__] * (REQUESTS - 1) + ["Review"]
    assert Review.objects.filter(status="running").count() == 1
