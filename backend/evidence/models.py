"""
Evidence app models.

Implements a **multi-table inheritance** hierarchy so every evidence
sub-type shares a common base table (``Evidence``) while storing its
type-specific fields in a dedicated table.

Evidence types (per project-doc §4.3):
    1. Witness / Local Testimony   – text statements + media files
    2. Biological / Medical        – forensic items verified by the Coroner
    3. Vehicle                     – XOR constraint: plate OR serial, never both
    4. Identity Document           – owner name + dynamic key-value details (JSONField)
    5. Other Item                  – title + description only (uses base ``Evidence``)
"""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


# ────────────────────────────────────────────────────────────────────
# Choice enumerations
# ────────────────────────────────────────────────────────────────────

class EvidenceType(models.TextChoices):
    """Discriminator stored on the base ``Evidence`` row."""

    TESTIMONY = "testimony", "Witness / Local Testimony"
    BIOLOGICAL = "biological", "Biological / Medical"
    VEHICLE = "vehicle", "Vehicle"
    IDENTITY = "identity", "Identity Document"
    OTHER = "other", "Other Item"


class FileType(models.TextChoices):
    """Allowed media types for ``EvidenceFile``."""

    IMAGE = "image", "Image"
    VIDEO = "video", "Video"
    AUDIO = "audio", "Audio"
    DOCUMENT = "document", "Document"


# ────────────────────────────────────────────────────────────────────
# Base evidence model
# ────────────────────────────────────────────────────────────────────

class Evidence(TimeStampedModel):
    """
    Base evidence record attached to a ``Case``.

    All evidence shares:
        • a title and a description
        • a registration date (``created_at`` from ``TimeStampedModel``)
        • a registrar (``registered_by``)
        • an ``evidence_type`` discriminator

    For the "Other Item" category the base model is sufficient — no
    child table is needed.
    """

    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="evidences",
        verbose_name="Case",
    )
    evidence_type = models.CharField(
        max_length=20,
        choices=EvidenceType.choices,
        verbose_name="Evidence Type",
        db_index=True,
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
    )
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registered_evidences",
        verbose_name="Registered By",
    )

    class Meta:
        verbose_name = "Evidence"
        verbose_name_plural = "Evidences"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_evidence_type_display()}] {self.title}"


# ────────────────────────────────────────────────────────────────────
# Child evidence types (multi-table inheritance)
# ────────────────────────────────────────────────────────────────────

class TestimonyEvidence(Evidence):
    """
    Witness or local testimony (§4.3.1).

    Includes a transcript of the witness's statement.  Images, videos,
    and audio recordings are stored via related ``EvidenceFile`` rows.
    """

    statement_text = models.TextField(
        blank=True,
        default="",
        verbose_name="Statement Transcript",
    )

    class Meta:
        verbose_name = "Testimony Evidence"
        verbose_name_plural = "Testimony Evidences"

    def save(self, *args, **kwargs):
        self.evidence_type = EvidenceType.TESTIMONY
        super().save(*args, **kwargs)


class BiologicalEvidence(Evidence):
    """
    Biological / medical evidence requiring forensic examination (§4.3.2).

    Examples: blood stains, hair strands, fingerprints.
    The ``forensic_result`` is initially empty and filled in by the
    Coroner after examination.
    """

    forensic_result = models.TextField(
        blank=True,
        default="",
        verbose_name="Forensic Result",
        help_text="Filled by the Coroner or national-identity DB verification.",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_biological_evidences",
        verbose_name="Verified By (Coroner)",
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Verified",
    )

    class Meta:
        verbose_name = "Biological Evidence"
        verbose_name_plural = "Biological Evidences"

    def save(self, *args, **kwargs):
        self.evidence_type = EvidenceType.BIOLOGICAL
        super().save(*args, **kwargs)


class VehicleEvidence(Evidence):
    """
    Vehicle evidence (§4.3.3).

    A vehicle connected to the crime scene.  Either a ``license_plate``
    **or** a ``serial_number`` must be provided — but **never both**
    at the same time (enforced by a CHECK constraint).
    """

    vehicle_model = models.CharField(
        max_length=100,
        verbose_name="Vehicle Model",
    )
    color = models.CharField(
        max_length=50,
        verbose_name="Color",
    )
    license_plate = models.CharField(
        max_length=20,
        blank=True,
        default="",
        verbose_name="License Plate",
    )
    serial_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Serial Number",
    )

    class Meta:
        verbose_name = "Vehicle Evidence"
        verbose_name_plural = "Vehicle Evidences"
        constraints = [
            # XOR: exactly one of license_plate / serial_number must be set.
            models.CheckConstraint(
                condition=(
                    models.Q(license_plate="", serial_number__gt="")
                    | models.Q(license_plate__gt="", serial_number="")
                ),
                name="vehicle_plate_xor_serial",
            ),
        ]

    def save(self, *args, **kwargs):
        self.evidence_type = EvidenceType.VEHICLE
        super().save(*args, **kwargs)


class IdentityEvidence(Evidence):
    """
    Identity-document evidence (§4.3.4).

    An ID document found at the crime scene.  ``document_details`` stores
    arbitrary key-value pairs (e.g. ``{"ID Number": "123", "Issue Date": …}``).
    The quantity and keys are **not** fixed — even zero pairs is valid.
    """

    owner_full_name = models.CharField(
        max_length=255,
        verbose_name="Document Owner's Full Name",
    )
    document_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Document Details (key-value)",
        help_text="Dynamic key-value pairs describing the document.",
    )

    class Meta:
        verbose_name = "Identity Evidence"
        verbose_name_plural = "Identity Evidences"

    def save(self, *args, **kwargs):
        self.evidence_type = EvidenceType.IDENTITY
        super().save(*args, **kwargs)


# ────────────────────────────────────────────────────────────────────
# Media files for any evidence type
# ────────────────────────────────────────────────────────────────────

class EvidenceFile(TimeStampedModel):
    """
    File attachment (image, video, audio, document) for any ``Evidence`` row.

    Used heavily for Testimony (media from locals) and Biological (photos
    of the sample) evidence types.
    """

    evidence = models.ForeignKey(
        Evidence,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Evidence",
    )
    file = models.FileField(
        upload_to="evidence_files/%Y/%m/",
        verbose_name="File",
    )
    file_type = models.CharField(
        max_length=10,
        choices=FileType.choices,
        verbose_name="File Type",
    )
    caption = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Caption",
    )

    class Meta:
        verbose_name = "Evidence File"
        verbose_name_plural = "Evidence Files"

    def __str__(self):
        return f"{self.get_file_type_display()} for Evidence #{self.evidence_id}"
