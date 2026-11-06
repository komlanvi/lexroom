import json
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from workspace.models import Document, Lawyer, SampleFinding


class Command(BaseCommand):
    help = "Load the sample lawyers and documents. Safe to run again: records are upserted by id."

    @transaction.atomic
    def handle(self, *args, **options):
        lawyers = self._read("lawyers.json")
        documents = self._read("documents.json")

        for lawyer in lawyers:
            Lawyer.objects.update_or_create(
                id=lawyer["id"], defaults={"name": lawyer["name"], "title": lawyer["title"]}
            )

        for document in documents:
            Document.objects.update_or_create(
                id=document["id"],
                defaults={
                    "title": document["title"],
                    "type": document["type"],
                    "pages": document["pages"],
                    "uploaded_at": datetime.fromisoformat(document["uploadedAt"]),
                    "uploaded_by_id": document["uploadedBy"],
                },
            )
        # Second pass: a document may supersede one listed after it.
        for document in documents:
            Document.objects.filter(id=document["id"]).update(supersedes_id=document["supersedes"])

        for document in documents:
            findings = document["findings"]
            for position, finding in enumerate(findings):
                SampleFinding.objects.update_or_create(
                    document_id=document["id"],
                    position=position,
                    defaults={
                        "clause": finding["clause"],
                        "title": finding["title"],
                        "severity": finding["severity"],
                        "excerpt": finding["excerpt"],
                        "explanation": finding["explanation"],
                    },
                )
            SampleFinding.objects.filter(document_id=document["id"], position__gte=len(findings)).delete()

        self.stdout.write(
            f"Seeded {len(lawyers)} lawyers, {len(documents)} documents "
            f"and {sum(len(d['findings']) for d in documents)} sample findings."
        )

    def _read(self, filename):
        with open(settings.SAMPLES_DIR / filename, encoding="utf-8") as file:
            return json.load(file)
