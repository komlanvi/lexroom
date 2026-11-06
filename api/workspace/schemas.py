from uuid import UUID

from ninja import Schema


class LawyerOut(Schema):
    id: UUID
    name: str
    title: str
