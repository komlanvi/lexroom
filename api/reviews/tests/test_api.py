from datetime import UTC, datetime, timedelta

import pytest

from reviews.models import FailureReason, Finding, Review, ReviewStatus
from reviews.services.lifecycle import add_finding, complete, fail_ai_error
from reviews.tests.helpers import DOCUMENTS, LAWYERS, T0, document, given_completed, given_review

pytestmark = pytest.mark.usefixtures("seeded")

NOW = datetime(2026, 11, 6, 10, 0, tzinfo=UTC)  # the fake_clock start
UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def post_review(client, document_name="nda", lawyer_id=LAWYERS["chiara"]):
    headers = {} if lawyer_id is None else {"X-Lawyer-Id": lawyer_id}
    return client.post(f"/api/documents/{DOCUMENTS[document_name]}/reviews", headers=headers)


# Documents


def test_documents_are_listed_newest_upload_first(client, fake_clock):
    documents = client.get("/api/documents").json()

    assert len(documents) == 13
    uploads = [document["uploaded_at"] for document in documents]
    assert uploads == sorted(uploads, reverse=True)
    assert documents[0]["id"] == DOCUMENTS["lease_v2"]


def test_document_list_links_both_lease_versions(client, fake_clock):
    documents = {document["id"]: document for document in client.get("/api/documents").json()}

    v1, v2 = documents[DOCUMENTS["lease_v1"]], documents[DOCUMENTS["lease_v2"]]
    assert (v2["supersedes"], v2["superseded_by"]) == (DOCUMENTS["lease_v1"], None)
    assert (v1["supersedes"], v1["superseded_by"]) == (None, DOCUMENTS["lease_v2"])
    others = [d for id_, d in documents.items() if id_ not in (DOCUMENTS["lease_v1"], DOCUMENTS["lease_v2"])]
    assert all(d["supersedes"] is None and d["superseded_by"] is None for d in others)


def test_document_never_reviewed(client, fake_clock):
    response = client.get(f"/api/documents/{DOCUMENTS['nda']}")

    assert response.status_code == 200
    assert response.json() == {
        "id": DOCUMENTS["nda"],
        "title": "Non-disclosure agreement — Alfa Robotics S.r.l.",
        "type": "nda",
        "pages": 4,
        "uploaded_at": "2026-09-01T08:42:00Z",
        "uploaded_by": LAWYERS["sofia"],
        "supersedes": None,
        "superseded_by": None,
        "latest_review": None,
        "current_result": None,
    }


def test_document_whose_last_attempt_failed_keeps_its_earlier_result(client, fake_clock):
    completed = given_review("nda", T0 - timedelta(days=5))
    Finding.objects.create(
        review=completed, seq=0, title="t", severity="high", explanation="e", received_at=completed.requested_at
    )
    failed = given_review("nda", T0 - timedelta(days=1), ReviewStatus.FAILED, FailureReason.TIMED_OUT)

    for body in (
        client.get(f"/api/documents/{DOCUMENTS['nda']}").json(),
        next(d for d in client.get("/api/documents").json() if d["id"] == DOCUMENTS["nda"]),
    ):
        assert body["latest_review"] == {
            "id": str(failed.id),
            "status": "failed",
            "failure_reason": "timed_out",
            "requested_by": LAWYERS["chiara"],
            "requested_at": iso(failed.requested_at),
            "deadline_at": iso(failed.deadline_at),
            "finished_at": iso(failed.finished_at),
        }
        assert body["current_result"] == {
            "review_id": str(completed.id),
            "finished_at": iso(completed.finished_at),
            "findings_count": 1,
        }


def test_completed_review_without_findings_is_a_result(client, fake_clock):
    review = given_review("nda", T0 - timedelta(days=1))

    body = client.get(f"/api/documents/{DOCUMENTS['nda']}").json()

    assert body["current_result"] == {"review_id": str(review.id), "finished_at": iso(review.finished_at), "findings_count": 0}


def test_unknown_document_is_404_with_error_body(client, fake_clock):
    response = client.get(f"/api/documents/{UNKNOWN_ID}")

    assert response.status_code == 404
    assert response.json() == {"code": "NOT_FOUND", "message": "Not found.", "details": {}}


def test_malformed_document_id_is_422_with_error_body(client):
    response = client.get("/api/documents/not-a-uuid")

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "INVALID_REQUEST"
    assert set(body) == {"code", "message", "details"}


# Requesting a review


def test_request_creates_a_running_review(client, fake_clock):
    response = post_review(client, lawyer_id=LAWYERS["sofia"])

    assert response.status_code == 201
    body = response.json()
    review = Review.objects.get()
    assert body == {
        "id": str(review.id),
        "document_id": DOCUMENTS["nda"],
        "status": "running",
        "failure_reason": None,
        "requested_by": LAWYERS["sofia"],
        "requested_at": iso(NOW),
        "deadline_at": iso(NOW + timedelta(seconds=60)),
        "finished_at": None,
        "server_now": iso(NOW),
        "is_final": False,
        "findings": [],
    }


def test_request_starts_the_fake_ai_after_commit(client, fake_clock, fake_ai_starts, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        response = post_review(client)

    assert fake_ai_starts == [Review.objects.get(id=response.json()["id"]).id]


@pytest.mark.parametrize(
    "lawyer_id", [None, "", "not-a-uuid", UNKNOWN_ID], ids=["missing", "empty", "malformed", "unknown"]
)
def test_request_without_a_known_lawyer_is_rejected(client, fake_clock, lawyer_id):
    response = post_review(client, lawyer_id=lawyer_id)

    assert response.status_code == 400
    assert response.json()["code"] == "UNKNOWN_LAWYER"
    assert set(response.json()) == {"code", "message", "details"}
    assert not Review.objects.exists()


def test_request_on_an_unknown_document_is_404(client, fake_clock):
    response = client.post(f"/api/documents/{UNKNOWN_ID}/reviews", headers={"X-Lawyer-Id": LAWYERS["chiara"]})

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_request_on_a_document_under_review_returns_the_running_review(client, fake_clock):
    running = post_review(client, lawyer_id=LAWYERS["chiara"]).json()

    response = post_review(client, lawyer_id=LAWYERS["sofia"])

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "REVIEW_IN_PROGRESS"
    assert body["details"]["review"]["id"] == running["id"]
    assert body["details"]["review"]["requested_by"] == LAWYERS["chiara"]
    assert body["details"]["review"]["deadline_at"] == running["deadline_at"]
    assert Review.objects.count() == 1


def test_request_when_the_plan_is_used_up(client, fake_clock):
    given_completed(9, requested_at=T0 - timedelta(hours=1))
    post_review(client, "loan")

    response = post_review(client, "nda")

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "PLAN_EXHAUSTED"
    assert datetime.fromisoformat(body["details"].pop("resets_at")) == datetime(2026, 11, 30, 23, 0, tzinfo=UTC)
    assert body["details"] == {"completed": 9, "running": 1}
    assert not Review.objects.filter(document=document("nda")).exists()


# Following and reading a review


def test_running_review_returns_its_partial_findings_in_arrival_order(client, fake_clock):
    review_id = post_review(client).json()["id"]
    samples = list(document("nda").sample_findings.all())
    add_finding(review_id, 0, samples[2], NOW + timedelta(seconds=5))
    add_finding(review_id, 1, samples[0], NOW + timedelta(seconds=8))
    fake_clock.advance(seconds=10)

    body = client.get(f"/api/reviews/{review_id}").json()

    assert (body["status"], body["is_final"]) == ("running", False)
    assert body["server_now"] == iso(NOW + timedelta(seconds=10))
    assert [f["seq"] for f in body["findings"]] == [0, 1]
    assert body["findings"][0] == {
        "seq": 0,
        "clause": None,
        "title": samples[2].title,
        "severity": samples[2].severity,
        "excerpt": None,
        "explanation": samples[2].explanation,
    }


def test_completed_review_is_final_with_all_its_findings(client, fake_clock):
    review_id = post_review(client).json()["id"]
    for seq, sample in enumerate(document("nda").sample_findings.all()):
        add_finding(review_id, seq, sample, NOW + timedelta(seconds=seq + 1))
    complete(review_id, NOW + timedelta(seconds=20))
    fake_clock.advance(seconds=20)

    body = client.get(f"/api/reviews/{review_id}").json()

    assert (body["status"], body["is_final"], len(body["findings"])) == ("completed", True, 3)
    assert body["finished_at"] == iso(NOW + timedelta(seconds=20))


def test_failed_review_exposes_no_findings(client, fake_clock):
    review_id = post_review(client).json()["id"]
    for seq, sample in enumerate(list(document("nda").sample_findings.all())[:2]):
        add_finding(review_id, seq, sample, NOW + timedelta(seconds=seq + 1))
    fail_ai_error(review_id, NOW + timedelta(seconds=10))

    body = client.get(f"/api/reviews/{review_id}").json()

    assert (body["status"], body["failure_reason"], body["is_final"]) == ("failed", "ai_error", False)
    assert body["findings"] == []
    assert Review.objects.get(id=review_id).findings.count() == 2


def test_overdue_review_is_reported_as_timed_out_without_its_findings(client, fake_clock):
    review_id = post_review(client).json()["id"]
    add_finding(review_id, 0, document("nda").sample_findings.first(), NOW + timedelta(seconds=5))
    fake_clock.advance(seconds=60)

    body = client.get(f"/api/reviews/{review_id}").json()

    assert (body["status"], body["failure_reason"]) == ("failed", "timed_out")
    assert body["finished_at"] == iso(NOW + timedelta(seconds=60))
    assert body["findings"] == []


def test_unknown_review_is_404(client, fake_clock):
    response = client.get(f"/api/reviews/{UNKNOWN_ID}")

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
