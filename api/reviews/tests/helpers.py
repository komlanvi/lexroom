from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from reviews.models import Review, ReviewStatus
from workspace.models import Document, Lawyer

ROME = ZoneInfo("Europe/Rome")
T0 = datetime(2026, 11, 6, 10, 0, tzinfo=ROME)

DOCUMENTS = {
    "nda": "639fb780-cfdf-4393-bf6e-6a330940b21e",
    "lease_v1": "125c8706-e702-4d6f-b2c5-80aeb110cd5c",
    "lease_v2": "a8d4c1e0-5f3b-4b7a-9e2d-6c1f0b3a7d58",
    "saas": "d6c1f51a-a15e-4502-923a-656eed71bcc7",
    "supply": "9545d54a-7e23-4b56-b2a3-01bf5d3b326f",
    "loan": "3ce07ee8-540f-4598-be28-038ff929e704",
    "consulting": "077070a7-519b-411e-a466-3c97db7f07ff",
    "franchise": "61a3bea4-f6cf-4854-92b6-671ae1349309",
}
LAWYERS = {
    "chiara": "7c1f3d2a-9b64-4e0f-8a21-5d3e6f7a8b90",
    "riccardo": "e4a8b6c2-1d3f-4a5b-9c7e-2f8a9b0c1d2e",
    "sofia": "3b9d2e1f-6a7c-4d8e-b0f1-9a2b3c4d5e6f",
}


def document(name: str) -> Document:
    return Document.objects.get(id=DOCUMENTS[name])


def lawyer(name: str) -> Lawyer:
    return Lawyer.objects.get(id=LAWYERS[name])


def given_review(
    document_name: str,
    requested_at: datetime,
    status: str = ReviewStatus.COMPLETED,
    failure_reason: str | None = None,
) -> Review:
    """A review stored directly in the database, as if it had happened earlier."""
    return Review.objects.create(
        document=document(document_name),
        requested_by=lawyer("chiara"),
        requested_at=requested_at,
        deadline_at=requested_at + timedelta(seconds=60),
        status=status,
        failure_reason=failure_reason,
        finished_at=None if status == ReviewStatus.RUNNING else requested_at + timedelta(seconds=10),
    )


def given_completed(count: int, requested_at: datetime = T0 - timedelta(days=1)) -> None:
    for _ in range(count):
        given_review("franchise", requested_at)
