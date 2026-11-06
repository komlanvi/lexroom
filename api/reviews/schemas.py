from datetime import datetime

from ninja import Schema


class PlanOut(Schema):
    limit: int
    completed: int
    running: int
    available: int
    period: str
    resets_at: datetime
