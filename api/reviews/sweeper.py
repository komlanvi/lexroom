"""Expires overdue reviews in the background, so they show as failed even when nobody reads them.

Correctness does not depend on it: every read and every request applies the same expiry first.
"""

import logging
import threading
import time

from django.db import connection

from reviews import clock as clock_module
from reviews.services.expiry import expire_overdue

logger = logging.getLogger(__name__)

INTERVAL_S = 5


def start() -> None:
    threading.Thread(target=_sweep_forever, daemon=True, name="review-sweeper").start()


def _sweep_forever() -> None:
    while True:
        time.sleep(INTERVAL_S)
        try:
            expired = expire_overdue(clock_module.clock.now())
            if expired:
                logger.info("Sweeper expired %s review(s).", expired)
        except Exception:
            logger.exception("Sweeper failed; retrying in %s s.", INTERVAL_S)
        finally:
            connection.close()
