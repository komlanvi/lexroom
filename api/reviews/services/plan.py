from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings

from reviews.models import Review, ReviewStatus


@dataclass(frozen=True)
class Plan:
    limit: int
    completed: int
    running: int
    available: int
    period: str
    resets_at: datetime


def plan_month(now: datetime) -> tuple[datetime, datetime]:
    """Start (inclusive) and end (exclusive) of the plan month containing `now`, in the plan time zone."""
    local = now.astimezone(ZoneInfo(settings.PLAN_TZ))
    start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def get_plan(now: datetime) -> Plan:
    """BR-2: completed and still-running reviews requested this month both use a slot."""
    start, end = plan_month(now)
    requested_this_month = Review.objects.filter(requested_at__gte=start, requested_at__lt=end)
    completed = requested_this_month.filter(status=ReviewStatus.COMPLETED).count()
    running = requested_this_month.filter(status=ReviewStatus.RUNNING, deadline_at__gt=now).count()
    return Plan(
        limit=settings.PLAN_LIMIT,
        completed=completed,
        running=running,
        available=max(0, settings.PLAN_LIMIT - completed - running),
        period=start.strftime("%Y-%m"),
        resets_at=end,
    )
