"""
Core app models.

Provides abstract base models and shared utilities used across the project.
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating ``created_at`` and
    ``updated_at`` timestamp fields for every concrete child model.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Updated At",
    )

    class Meta:
        abstract = True


class Notification(TimeStampedModel):
    """
    System notification sent to a user regarding case updates, evidence
    additions, approval/rejection events, bounty verifications, etc.

    Uses a GenericForeignKey so any model instance can be the *source* of a
    notification (e.g. a new Evidence added to a case notifies the Detective).
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Recipient",
    )
    title = models.CharField(max_length=255, verbose_name="Title")
    message = models.TextField(verbose_name="Message")
    is_read = models.BooleanField(default=False, verbose_name="Read")

    # Generic relation to the object that triggered the notification
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Related Content Type",
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Related Object ID",
    )
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"[{self.recipient}] {self.title}"
