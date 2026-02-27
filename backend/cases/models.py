"""
Cases app models.

Covers the complete case lifecycle — from initial complaint registration or
crime-scene report, through cadet/officer review, detective investigation,
sergeant/captain/chief approval, all the way to judiciary referral and
closure.
"""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from core.permissions_constants import CasesPerms


# ────────────────────────────────────────────────────────────────────
# Choice enumerations
# ────────────────────────────────────────────────────────────────────

class CrimeLevel(models.IntegerChoices):
    """
    Crime severity levels.  The *integer value* doubles as the crime
    **degree** used in the Most-Wanted ranking formula
    (``max(days_wanted) × max(crime_degree)``).

    Level 3 (minor) → degree 1  …  Critical → degree 4.
    """

    LEVEL_3 = 1, "Level 3 (Minor)"       # petty theft, minor fraud
    LEVEL_2 = 2, "Level 2 (Medium)"      # auto theft
    LEVEL_1 = 3, "Level 1 (Major)"       # murder
    CRITICAL = 4, "Critical"             # serial killings, VIP assassination


class CaseStatus(models.TextChoices):
    """
    Unified status list that covers *both* creation workflows plus the
    common investigation/trial pipeline.
    """

    # ── Complaint workflow ───────────────────────────────────────────
    COMPLAINT_REGISTERED = "complaint_registered", "Complaint Registered"
    CADET_REVIEW = "cadet_review", "Under Cadet Review"
    RETURNED_TO_COMPLAINANT = "returned_to_complainant", "Returned to Complainant"
    OFFICER_REVIEW = "officer_review", "Under Officer Review"
    RETURNED_TO_CADET = "returned_to_cadet", "Returned to Cadet"
    VOIDED = "voided", "Voided"

    # ── Crime-scene workflow ─────────────────────────────────────────
    PENDING_APPROVAL = "pending_approval", "Pending Superior Approval"

    # ── Common statuses (after case is officially opened) ────────────
    OPEN = "open", "Open"
    INVESTIGATION = "investigation", "Under Investigation"
    JUDICIARY = "judiciary", "Referred to Judiciary"
    CLOSED = "closed", "Closed"


class CaseCreationType(models.TextChoices):
    """How the case originated."""

    COMPLAINT = "complaint", "Via Complaint"
    CRIME_SCENE = "crime_scene", "Via Crime-Scene Report"


class ComplainantStatus(models.TextChoices):
    """Approval status for a complainant linked to a case."""

    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


# ────────────────────────────────────────────────────────────────────
# Models
# ────────────────────────────────────────────────────────────────────

class Case(TimeStampedModel):
    """
    Central entity of the system — a police case.

    * Created either via *complaint registration* (citizen files a complaint)
      or *crime-scene registration* (officer witnesses / receives a report).
    * Tracks the full workflow status, crime severity, key assigned personnel,
      and complaint-rejection counter (3 rejections → case is **voided**).
    """

    title = models.CharField(
        max_length=255,
        verbose_name="Case Title",
    )
    description = models.TextField(
        verbose_name="Description",
    )
    crime_level = models.IntegerField(
        choices=CrimeLevel.choices,
        verbose_name="Crime Level",
        db_index=True,
        help_text="Determines severity and affects Most-Wanted ranking formula.",
    )
    status = models.CharField(
        max_length=30,
        choices=CaseStatus.choices,
        default=CaseStatus.COMPLAINT_REGISTERED,
        verbose_name="Current Status",
        db_index=True,
    )
    creation_type = models.CharField(
        max_length=20,
        choices=CaseCreationType.choices,
        verbose_name="Creation Type",
    )

    # ── Complaint-workflow tracking ─────────────────────────────────
    rejection_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name="Rejection Count",
        help_text="If this reaches 3 the case is voided automatically.",
    )

    # ── When / where the incident occurred ──────────────────────────
    incident_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Incident Date/Time",
    )
    location = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="Incident Location",
    )

    # ── Key personnel ───────────────────────────────────────────────
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_cases",
        verbose_name="Created By",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_cases",
        verbose_name="Approved By",
        help_text="Superior who approved the case (crime-scene workflow).",
    )
    assigned_detective = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detective_cases",
        verbose_name="Assigned Detective",
    )
    assigned_sergeant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sergeant_cases",
        verbose_name="Assigned Sergeant",
    )
    assigned_captain = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="captain_cases",
        verbose_name="Assigned Captain",
    )
    assigned_judge = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="judge_cases",
        verbose_name="Assigned Judge",
    )

    class Meta:
        verbose_name = "Case"
        verbose_name_plural = "Cases"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["creation_type"]),
            models.Index(fields=["status", "crime_level"]),
        ]
        permissions = [
            (CasesPerms.CAN_REVIEW_COMPLAINT, "Can review incoming complaints (Cadet)"),
            (CasesPerms.CAN_APPROVE_CASE, "Can approve a case after review"),
            (CasesPerms.CAN_ASSIGN_DETECTIVE, "Can assign a detective to a case"),
            (CasesPerms.CAN_CHANGE_CASE_STATUS, "Can transition case workflow status"),
            (CasesPerms.CAN_FORWARD_TO_JUDICIARY, "Can forward solved case to judiciary"),
            (CasesPerms.CAN_APPROVE_CRITICAL_CASE, "Can approve critical-level cases (Chief)"),
            # Scope permissions (data-visibility tiers)
            (CasesPerms.CAN_SCOPE_ALL_CASES, "Unrestricted case visibility"),
            (CasesPerms.CAN_SCOPE_SUPERVISED_CASES, "See supervised cases (Sergeant)"),
            (CasesPerms.CAN_SCOPE_ASSIGNED_CASES, "See only assigned cases (Detective)"),
            (CasesPerms.CAN_SCOPE_OFFICER_CASES, "See post-complaint cases (Officer)"),
            (CasesPerms.CAN_SCOPE_COMPLAINT_QUEUE, "See early complaint queue (Cadet)"),
            (CasesPerms.CAN_SCOPE_JUDICIARY_CASES, "See judiciary/closed cases (Judge)"),
            (CasesPerms.CAN_SCOPE_OWN_CASES, "See only own-involved cases"),
            (CasesPerms.CAN_SCOPE_CORONER_CASES, "See cases with unverified bio evidence (Coroner)"),
            # Workflow guard permissions
            (CasesPerms.CAN_CREATE_CRIME_SCENE, "Can create a crime-scene case"),
            (CasesPerms.CAN_AUTO_APPROVE_CRIME_SCENE, "Crime-scene cases auto-open on creation"),
            (CasesPerms.CAN_VIEW_CASE_REPORT, "Can access the full case report"),
            # Assignment capability permissions
            (CasesPerms.CAN_BE_ASSIGNED_DETECTIVE, "Can be assigned as detective"),
            (CasesPerms.CAN_BE_ASSIGNED_SERGEANT, "Can be assigned as sergeant"),
            (CasesPerms.CAN_BE_ASSIGNED_CAPTAIN, "Can be assigned as captain"),
            (CasesPerms.CAN_BE_ASSIGNED_JUDGE, "Can be assigned as judge"),
        ]

    def __str__(self):
        return f"Case #{self.pk} — {self.title}"

    @property
    def is_open(self) -> bool:
        """Return True if the case is still active (not closed/voided)."""
        return self.status not in (CaseStatus.CLOSED, CaseStatus.VOIDED)


class CaseComplainant(TimeStampedModel):
    """
    Junction table that links one or more complainants to a case.

    * For *complaint-created* cases the primary complainant
      (``is_primary=True``) is the citizen who filed the complaint.
    * Additional complainants can be added to any case type.
    * A Cadet approves or rejects each complainant's information.
    """

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="complainants",
        verbose_name="Case",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="case_complaints",
        verbose_name="Complainant",
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name="Primary Complainant",
    )
    status = models.CharField(
        max_length=10,
        choices=ComplainantStatus.choices,
        default=ComplainantStatus.PENDING,
        verbose_name="Approval Status",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_complainants",
        verbose_name="Reviewed By",
    )

    class Meta:
        verbose_name = "Case Complainant"
        verbose_name_plural = "Case Complainants"
        unique_together = [("case", "user")]

    def __str__(self):
        kind = "Primary" if self.is_primary else "Additional"
        return f"{kind} complainant {self.user} on Case #{self.case_id}"


class CaseWitness(TimeStampedModel):
    """
    Witness recorded for a crime-scene case.

    Witnesses are **not** required to be registered system users; only
    their phone number and national ID are stored for follow-up.
    """

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="witnesses",
        verbose_name="Case",
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name="Full Name",
    )
    phone_number = models.CharField(
        max_length=15,
        verbose_name="Phone Number",
    )
    national_id = models.CharField(
        max_length=10,
        verbose_name="National ID",
        db_index=True,
    )

    class Meta:
        verbose_name = "Case Witness"
        verbose_name_plural = "Case Witnesses"

    def __str__(self):
        return f"Witness {self.full_name} on Case #{self.case_id}"


class CaseStatusLog(TimeStampedModel):
    """
    Immutable audit trail of every status transition for a case.

    Stores the previous/new status, who made the change, and an optional
    message (e.g. the Cadet's rejection reason sent back to the complainant).
    """

    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="status_logs",
        verbose_name="Case",
    )
    from_status = models.CharField(
        max_length=30,
        choices=CaseStatus.choices,
        verbose_name="Previous Status",
    )
    to_status = models.CharField(
        max_length=30,
        choices=CaseStatus.choices,
        verbose_name="New Status",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="case_status_changes",
        verbose_name="Changed By",
    )
    message = models.TextField(
        blank=True,
        default="",
        verbose_name="Message / Rejection Reason",
    )

    class Meta:
        verbose_name = "Case Status Log"
        verbose_name_plural = "Case Status Logs"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Case #{self.case_id}: "
            f"{self.from_status} → {self.to_status}"
        )
