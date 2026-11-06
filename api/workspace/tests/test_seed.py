import io
import json
import shutil
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import call_command

from reviews.models import Review
from workspace.models import Document, Lawyer, SampleFinding

LEASE_V1 = "125c8706-e702-4d6f-b2c5-80aeb110cd5c"
LEASE_V2 = "a8d4c1e0-5f3b-4b7a-9e2d-6c1f0b3a7d58"
CONSULTING = "077070a7-519b-411e-a466-3c97db7f07ff"


def load_samples(name):
    with open(settings.SAMPLES_DIR / name, encoding="utf-8") as file:
        return json.load(file)


def seed():
    call_command("seed", stdout=io.StringIO())


def database_snapshot():
    return (
        list(Lawyer.objects.order_by("id").values()),
        list(Document.objects.order_by("id").values()),
        list(SampleFinding.objects.order_by("id").values()),
    )


def test_seed_loads_every_sample_field_for_field(db):
    seed()

    lawyers = load_samples("lawyers.json")
    documents = load_samples("documents.json")
    assert (len(lawyers), len(documents)) == (3, 13)
    assert sum(len(d["findings"]) for d in documents) == 47

    assert Lawyer.objects.count() == 3
    for lawyer in lawyers:
        assert Lawyer.objects.filter(**lawyer).exists()

    assert Document.objects.count() == 13
    assert SampleFinding.objects.count() == 47
    for sample in documents:
        document = Document.objects.get(id=sample["id"])
        assert document.title == sample["title"]
        assert document.type == sample["type"]
        assert document.pages == sample["pages"]
        assert document.uploaded_at == datetime.fromisoformat(sample["uploadedAt"])
        assert str(document.uploaded_by_id) == sample["uploadedBy"]
        assert (str(document.supersedes_id) if document.supersedes_id else None) == sample["supersedes"]
        stored = list(
            document.sample_findings.values("position", "clause", "title", "severity", "excerpt", "explanation")
        )
        expected = [{"position": i, **finding} for i, finding in enumerate(sample["findings"])]
        assert stored == expected


def test_seed_links_the_superseded_lease(db):
    seed()

    lease_v2 = Document.objects.get(id=LEASE_V2)
    assert str(lease_v2.supersedes_id) == LEASE_V1
    assert str(Document.objects.get(id=LEASE_V1).superseded_by.id) == LEASE_V2
    assert Document.objects.exclude(supersedes=None).count() == 1


def test_seed_keeps_missing_clause_and_excerpt_as_null(db):
    seed()

    missing = SampleFinding.objects.filter(clause=None)
    assert missing.count() == 3
    assert all(finding.excerpt is None for finding in missing)


def test_seed_keeps_a_document_without_findings(db):
    seed()

    assert Document.objects.get(id=CONSULTING).sample_findings.count() == 0


def test_seed_twice_changes_nothing(db):
    seed()
    before = database_snapshot()

    seed()

    assert database_snapshot() == before


def test_seed_keeps_existing_reviews(db):
    seed()
    document = Document.objects.get(id=LEASE_V2)
    review = Review.objects.create(
        document=document,
        requested_by=document.uploaded_by,
        requested_at=document.uploaded_at,
        deadline_at=document.uploaded_at + timedelta(seconds=60),
    )

    seed()

    assert Review.objects.filter(id=review.id).exists()


def test_seed_updates_changed_samples_and_drops_removed_findings(db, settings, tmp_path):
    for name in ("lawyers.json", "documents.json"):
        shutil.copy(settings.SAMPLES_DIR / name, tmp_path / name)
    settings.SAMPLES_DIR = tmp_path
    seed()

    documents = load_samples("documents.json")
    lease = next(d for d in documents if d["id"] == LEASE_V2)
    lease["title"] = "Renamed lease"
    lease["findings"] = lease["findings"][:1]
    (tmp_path / "documents.json").write_text(json.dumps(documents), encoding="utf-8")
    seed()

    document = Document.objects.get(id=LEASE_V2)
    assert document.title == "Renamed lease"
    assert list(document.sample_findings.values_list("title", flat=True)) == [lease["findings"][0]["title"]]
    assert Document.objects.count() == 13
