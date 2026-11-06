from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router

from workspace.models import Document, Lawyer
from workspace.schemas import DocumentOut, LawyerOut

router = Router()


@router.get("/lawyers", response=list[LawyerOut])
def list_lawyers(request):
    return Lawyer.objects.order_by("name")


@router.get("/documents", response=list[DocumentOut])
def list_documents(request):
    return Document.objects.select_related("superseded_by").order_by("-uploaded_at")


@router.get("/documents/{document_id}", response=DocumentOut)
def get_document(request, document_id: UUID):
    return get_object_or_404(Document.objects.select_related("superseded_by"), id=document_id)
