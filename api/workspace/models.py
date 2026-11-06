from django.db import models


class Severity(models.TextChoices):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Lawyer(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Document(models.Model):
    id = models.UUIDField(primary_key=True)
    title = models.CharField(max_length=300)
    type = models.CharField(max_length=50)
    pages = models.PositiveIntegerField()
    uploaded_at = models.DateTimeField()
    uploaded_by = models.ForeignKey(Lawyer, on_delete=models.PROTECT, related_name="uploaded_documents")
    supersedes = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by"
    )

    def __str__(self):
        return self.title


class SampleFinding(models.Model):
    """A finding the fake AI will report for this document, in `position` order."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="sample_findings")
    position = models.PositiveIntegerField()
    clause = models.CharField(max_length=50, null=True, blank=True)
    title = models.CharField(max_length=300)
    severity = models.CharField(max_length=10, choices=Severity.choices)
    excerpt = models.TextField(null=True, blank=True)
    explanation = models.TextField()

    class Meta:
        ordering = ["document", "position"]
        constraints = [
            models.UniqueConstraint(fields=["document", "position"], name="unique_sample_finding_position"),
        ]
