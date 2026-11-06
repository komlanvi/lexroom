from datetime import datetime
from uuid import UUID

from ninja import Field, Schema

from workspace.models import Document


class LawyerOut(Schema):
    id: UUID
    name: str
    title: str


class DocumentOut(Schema):
    id: UUID
    title: str
    type: str
    pages: int
    uploaded_at: datetime
    uploaded_by: UUID = Field(alias="uploaded_by_id")
    supersedes: UUID | None = Field(alias="supersedes_id")
    superseded_by: UUID | None

    @staticmethod
    def resolve_superseded_by(document: Document) -> UUID | None:
        try:
            return document.superseded_by.id
        except Document.superseded_by.RelatedObjectDoesNotExist:
            return None
