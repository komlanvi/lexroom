import uuid

from django.db import models
from django.db.models import Q

from workspace.models import Document, Lawyer, Severity


class ReviewStatus(models.TextChoices):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FailureReason(models.TextChoices):
    AI_ERROR = "ai_error"
    TIMED_OUT = "timed_out"


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name="reviews")
    requested_by = models.ForeignKey(Lawyer, on_delete=models.PROTECT, related_name="requested_reviews")
    requested_at = models.DateTimeField()
    deadline_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=ReviewStatus.choices, default=ReviewStatus.RUNNING)
    failure_reason = models.CharField(max_length=10, choices=FailureReason.choices, null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document"],
                condition=Q(status=ReviewStatus.RUNNING),
                name="one_running_review_per_document",
            ),
            models.CheckConstraint(
                condition=Q(status__in=ReviewStatus.values),
                name="review_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    # isnull=False matters: in SQL, NULL IN (...) is unknown, which a CHECK accepts.
                    Q(status=ReviewStatus.FAILED, failure_reason__isnull=False, failure_reason__in=FailureReason.values)
                    | (~Q(status=ReviewStatus.FAILED) & Q(failure_reason__isnull=True))
                ),
                name="failure_reason_only_when_failed",
            ),
        ]
        indexes = [models.Index(fields=["status", "requested_at"])]


class Finding(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="findings")
    seq = models.PositiveIntegerField(help_text="Arrival order within the review.")
    clause = models.CharField(max_length=50, null=True, blank=True)
    title = models.CharField(max_length=300)
    severity = models.CharField(max_length=10, choices=Severity.choices)
    excerpt = models.TextField(null=True, blank=True)
    explanation = models.TextField()
    received_at = models.DateTimeField()

    class Meta:
        ordering = ["review", "seq"]
        constraints = [
            models.UniqueConstraint(fields=["review", "seq"], name="unique_finding_seq"),
        ]
