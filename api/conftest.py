import io
from datetime import UTC, datetime

import pytest
from django.core.management import call_command

from reviews import clock as clock_module
from reviews.clock import FakeClock


@pytest.fixture
def seeded(db):
    call_command("seed", stdout=io.StringIO())


@pytest.fixture
def fake_clock(monkeypatch):
    fake = FakeClock(datetime(2026, 11, 6, 10, 0, tzinfo=UTC))
    monkeypatch.setattr(clock_module, "clock", fake)
    return fake
