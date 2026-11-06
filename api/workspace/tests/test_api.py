import pytest

LEASE_V1 = "125c8706-e702-4d6f-b2c5-80aeb110cd5c"
LEASE_V2 = "a8d4c1e0-5f3b-4b7a-9e2d-6c1f0b3a7d58"
NDA = "639fb780-cfdf-4393-bf6e-6a330940b21e"

pytestmark = pytest.mark.usefixtures("seeded")


def test_lawyers_are_listed_by_name(client):
    response = client.get("/api/lawyers")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "7c1f3d2a-9b64-4e0f-8a21-5d3e6f7a8b90", "name": "Chiara Belotti", "title": "Partner"},
        {"id": "e4a8b6c2-1d3f-4a5b-9c7e-2f8a9b0c1d2e", "name": "Riccardo Fanti", "title": "Senior associate"},
        {"id": "3b9d2e1f-6a7c-4d8e-b0f1-9a2b3c4d5e6f", "name": "Sofia Greco", "title": "Trainee lawyer"},
    ]


def test_documents_are_listed_newest_upload_first(client):
    documents = client.get("/api/documents").json()

    assert len(documents) == 13
    uploads = [document["uploaded_at"] for document in documents]
    assert uploads == sorted(uploads, reverse=True)
    assert documents[0]["id"] == LEASE_V2


def test_document_list_links_both_lease_versions(client):
    documents = {document["id"]: document for document in client.get("/api/documents").json()}

    assert documents[LEASE_V2]["supersedes"] == LEASE_V1
    assert documents[LEASE_V2]["superseded_by"] is None
    assert documents[LEASE_V1]["supersedes"] is None
    assert documents[LEASE_V1]["superseded_by"] == LEASE_V2
    others = [d for id_, d in documents.items() if id_ not in (LEASE_V1, LEASE_V2)]
    assert all(d["supersedes"] is None and d["superseded_by"] is None for d in others)


def test_document_detail(client):
    response = client.get(f"/api/documents/{NDA}")

    assert response.status_code == 200
    assert response.json() == {
        "id": NDA,
        "title": "Non-disclosure agreement — Alfa Robotics S.r.l.",
        "type": "nda",
        "pages": 4,
        "uploaded_at": "2026-09-01T08:42:00Z",
        "uploaded_by": "3b9d2e1f-6a7c-4d8e-b0f1-9a2b3c4d5e6f",
        "supersedes": None,
        "superseded_by": None,
    }


def test_unknown_document_is_404_with_error_body(client):
    response = client.get("/api/documents/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json() == {"code": "NOT_FOUND", "message": "Not found.", "details": {}}


def test_malformed_document_id_is_422_with_error_body(client):
    response = client.get("/api/documents/not-a-uuid")

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "INVALID_REQUEST"
    assert set(body) == {"code", "message", "details"}
