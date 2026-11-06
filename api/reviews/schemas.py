from datetime import datetime
from uuid import UUID

from ninja import Field, Schema

from reviews.models import Review, ReviewStatus
from workspace.models import Document


class PlanOut(Schema):
    limit: int
    completed: int
    running: int
    available: int
    period: str
    resets_at: datetime


class ReviewSummaryOut(Schema):
    id: UUID
    status: str
    failure_reason: str | None
    requested_by: UUID = Field(alias="requested_by_id")
    requested_at: datetime
    deadline_at: datetime
    finished_at: datetime | None


class FindingOut(Schema):
    seq: int
    clause: str | None
    title: str
    severity: str
    excerpt: str | None
    explanation: str


class ReviewOut(ReviewSummaryOut):
    document_id: UUID
    server_now: datetime
    is_final: bool
    findings: list[FindingOut]

    @staticmethod
    def resolve_is_final(review: Review) -> bool:
        return review.status == ReviewStatus.COMPLETED

    @staticmethod
    def resolve_findings(review: Review):
        # BR-16: a failed review's findings stay stored but are never exposed.
        if review.status == ReviewStatus.FAILED:
            return []
        return review.findings.all()


class ResultOut(Schema):
    review_id: UUID = Field(alias="id")
    finished_at: datetime
    findings_count: int

    @staticmethod
    def resolve_findings_count(review: Review) -> int:
        return review.findings.count()


class DocumentOut(Schema):
    id: UUID
    title: str
    type: str
    pages: int
    uploaded_at: datetime
    uploaded_by: UUID = Field(alias="uploaded_by_id")
    supersedes: UUID | None = Field(alias="supersedes_id")
    superseded_by: UUID | None
    latest_review: ReviewSummaryOut | None
    current_result: ResultOut | None

    @staticmethod
    def resolve_superseded_by(document: Document) -> UUID | None:
        try:
            return document.superseded_by.id
        except Document.superseded_by.RelatedObjectDoesNotExist:
            return None
