"""
core.domain.notifications — Synchronous notification creation helper.

Centralises notification creation so every app uses one consistent
entry-point rather than directly constructing ``Notification`` objects.

Design decisions
----------------
* **Synchronous for now** — all DB writes happen in the calling thread.
  When we're ready for async / background delivery, swap the ``_persist``
  call to ``transaction.on_commit(lambda: _persist(...))`` or push to
  a Celery task.  The public API (``NotificationService.create``) stays
  the same.
* **Supports multiple recipients** — pass a single ``User`` or an
  iterable of ``User`` instances.
* **Generic relation** — ``related_object`` is optional; if provided
  its ``ContentType`` and PK are stored via the ``Notification`` model's
  ``GenericForeignKey``.

Usage::

    from core.domain.notifications import NotificationService

    NotificationService.create(
        actor=request.user,
        recipients=case.assigned_detective,
        event_type="evidence_added",
        payload={"case_id": case.id, "evidence_id": evidence.id},
        related_object=evidence,
    )
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Iterable

from django.contrib.contenttypes.models import ContentType
from django.db import models

if TYPE_CHECKING:
    from accounts.models import User
    from core.models import Notification

logger = logging.getLogger(__name__)

# ── Event-type → human-readable templates ───────────────────────────
# Extend this dict as new event types are introduced in app services.
_EVENT_TEMPLATES: dict[str, tuple[str, str]] = {
    # event_type: (title_template, message_template)
    # Templates may use {actor}, {payload.*} interpolation in the future.
    "evidence_added":        ("New Evidence Added",       "New evidence has been registered for a case you are assigned to."),
    "bio_evidence_verified": ("Biological Evidence Verified", "Biological evidence in your case has been reviewed by the Coroner."),
    "case_status_changed":   ("Case Status Updated",     "A case you are involved with has changed status."),
    "suspect_needs_review":  ("Suspect Pending Review",  "A new suspect has been identified and requires your review."),
    "suspect_approved":      ("Suspect Approved",        "A suspect in your case has been approved."),
    "suspect_rejected":      ("Suspect Rejected",        "A suspect in your case has been rejected."),
    "interrogation_created": ("Interrogation Recorded",  "An interrogation has been logged for a suspect in your case."),
    "trial_created":         ("Trial Recorded",          "A trial verdict has been recorded for a suspect in your case."),
    "bounty_tip_submitted":  ("Bounty Tip Submitted",    "A citizen has submitted a bounty tip."),
    "bounty_tip_verified":   ("Bounty Tip Verified",     "A bounty tip you submitted has been verified."),
    "bail_payment":          ("Bail Payment",             "A bail payment has been processed."),
    "assignment_changed":    ("Assignment Updated",       "You have been assigned to or removed from a case."),
    "complaint_returned":    ("Complaint Returned",       "Your complaint has been returned for revision."),
    "case_approved":         ("Case Approved",            "A case has been approved."),
    "case_rejected":         ("Case Rejected",            "A case has been rejected."),
}


class NotificationService:
    """
    Stateless helper for creating ``Notification`` records.

    All methods are classmethods — no instance state is needed.
    """

    @classmethod
    def create(
        cls,
        *,
        actor: User,
        recipients: User | Iterable[User],
        event_type: str,
        payload: dict[str, Any] | None = None,
        related_object: models.Model | None = None,
    ) -> list[Notification]:
        """
        Create one ``Notification`` per recipient.

        Args:
            actor:          The user who performed the action (used for
                            audit / display — NOT stored as FK on the
                            current model, but included for future use).
            recipients:     A single ``User`` or iterable of ``User``
                            instances.
            event_type:     Key into ``_EVENT_TEMPLATES``.  If unknown
                            the raw event_type is used as title.
            payload:        Arbitrary context dict.  Not persisted to the
                            DB in the current schema but available for
                            template interpolation / logging.
            related_object: Optional model instance linked via
                            ``GenericForeignKey``.

        Returns:
            List of created ``Notification`` instances.
        """
        from core.models import Notification  # lazy import — avoids circular deps

        # Normalise recipients to a list
        if isinstance(recipients, models.Model):
            recipients = [recipients]
        else:
            recipients = list(recipients)

        if not recipients:
            logger.warning(
                "NotificationService.create called with empty recipients "
                "for event_type=%s by actor=%s",
                event_type,
                actor,
            )
            return []

        title, message = _EVENT_TEMPLATES.get(
            event_type,
            (event_type.replace("_", " ").title(), f"Event: {event_type}"),
        )

        # Resolve GenericFK fields
        content_type = None
        object_id = None
        if related_object is not None:
            content_type = ContentType.objects.get_for_model(related_object)
            object_id = related_object.pk

        notifications: list[Notification] = []
        for recipient in recipients:
            notif = Notification.objects.create(
                recipient=recipient,
                title=title,
                message=message,
                content_type=content_type,
                object_id=object_id,
            )
            notifications.append(notif)

        logger.info(
            "Created %d notification(s) [%s] by actor=%s",
            len(notifications),
            event_type,
            actor,
        )
        return notifications
