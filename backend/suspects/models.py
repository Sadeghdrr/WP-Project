"""
Suspects app models.

Covers the suspect lifecycle from identification through interrogation,
trial, verdict, and optional bail payment.  Also includes the public
bounty-tip workflow (citizen submits info → officer reviews → detective
verifies → reward issued).

Key computed properties:
    • ``Suspect.most_wanted_score`` — ranking formula:
      max(days_wanted across open cases) × max(crime_degree across all cases)
    • ``Suspect.reward_amount``      — bounty calculation in Rials.
    • ``Suspect.is_most_wanted``     — True when wanted > 30 days.
"""

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel
from core.permissions_constants import SuspectsPerms
from core.constants import REWARD_MULTIPLIER


# ────────────────────────────────────────────────────────────────────
# Choice enumerations
# ────────────────────────────────────────────────────────────────────

class SuspectStatus(models.TextChoices):
    """Status of a suspect within a single case."""

    WANTED = "wanted", "Wanted"
    ARRESTED = "arrested", "Arrested"
    UNDER_INTERROGATION = "under_interrogation", "Under Interrogation"
    PENDING_CAPTAIN_VERDICT = "pending_captain_verdict", "Pending Captain Verdict"
    PENDING_CHIEF_APPROVAL = "pending_chief_approval", "Pending Chief Approval"
    UNDER_TRIAL = "under_trial", "Under Trial"
    CONVICTED = "convicted", "Convicted"
    ACQUITTED = "acquitted", "Acquitted"
    RELEASED = "released", "Released on Bail"


class VerdictChoice(models.TextChoices):
    """Judge's verdict at trial."""

    GUILTY = "guilty", "Guilty"
    INNOCENT = "innocent", "Innocent"


class BountyTipStatus(models.TextChoices):
    """Review pipeline for citizen-submitted tips."""

    PENDING = "pending", "Pending Review"
    OFFICER_REVIEWED = "officer_reviewed", "Reviewed by Officer"
    VERIFIED = "verified", "Verified by Detective"
    REJECTED = "rejected", "Rejected"


# ────────────────────────────────────────────────────────────────────
# Models
# ────────────────────────────────────────────────────────────────────

class Suspect(TimeStampedModel):
    """
    Links an individual to a ``Case`` as a suspect.

    A person may be a suspect in multiple cases; each combination creates a
    separate ``Suspect`` row.  Cross-case aggregation for the Most-Wanted
    ranking is performed by grouping on ``national_id``.

    The suspect may optionally be linked to a registered ``User`` if they
    have an account; otherwise, their identity fields are stored directly.
    """

    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="suspects",
        verbose_name="Case",
    )
    # Optional link to system user
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suspect_records",
        verbose_name="Linked User Account",
    )

    # ── Identity fields (may duplicate User data for non-users) ─────
    full_name = models.CharField(
        max_length=255,
        verbose_name="Full Name",
    )
    national_id = models.CharField(
        max_length=10,
        blank=True,
        default="",
        verbose_name="National ID",
        db_index=True,
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        default="",
        verbose_name="Phone Number",
    )
    photo = models.ImageField(
        upload_to="suspect_photos/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="Photo",
    )
    address = models.TextField(
        blank=True,
        default="",
        verbose_name="Address",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Additional Description",
    )

    # ── Status tracking ─────────────────────────────────────────────
    status = models.CharField(
        max_length=30,
        choices=SuspectStatus.choices,
        default=SuspectStatus.WANTED,
        verbose_name="Status",
        db_index=True,
    )
    wanted_since = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Wanted Since",
        db_index=True,
    )
    arrested_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Arrested At",
    )

    # ── Who identified / approved ───────────────────────────────────
    identified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="identified_suspects",
        verbose_name="Identified By (Detective)",
    )
    approved_by_sergeant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sergeant_approved_suspects",
        verbose_name="Approved By (Sergeant)",
    )
    sergeant_approval_status = models.CharField(
        max_length=10,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="pending",
        verbose_name="Sergeant Approval",
    )
    sergeant_rejection_message = models.TextField(
        blank=True,
        default="",
        verbose_name="Sergeant Rejection Message",
    )

    class Meta:
        verbose_name = "Suspect"
        verbose_name_plural = "Suspects"
        ordering = ["-wanted_since"]
        indexes = [
            models.Index(fields=["status", "wanted_since"]),
        ]
        permissions = [
            (SuspectsPerms.CAN_IDENTIFY_SUSPECT, "Can identify and declare suspects (Detective)"),
            (SuspectsPerms.CAN_APPROVE_SUSPECT, "Can approve/reject identified suspects (Sergeant)"),
            (SuspectsPerms.CAN_ISSUE_ARREST_WARRANT, "Can issue arrest warrant (Sergeant)"),
        ]

    def __str__(self):
        return f"Suspect: {self.full_name} — Case #{self.case_id}"

    # ── Computed properties ─────────────────────────────────────────

    @property
    def days_wanted(self) -> int:
        """Number of days this suspect has been wanted in *this* case."""
        return (timezone.now() - self.wanted_since).days

    @property
    def is_most_wanted(self) -> bool:
        """
        A suspect is placed in the 'Most Wanted' status when they have
        been wanted for over 30 days (project-doc §4.7).
        """
        return self.days_wanted > 30

    @property
    def most_wanted_score(self) -> int:
        """
        Ranking formula (project-doc §4.7 Note 1)::

            score = max(Lj) × max(Di)

        Where:
            Lj = days wanted in each *open* case for this person
            Di = crime degree (1–4) of the highest-severity case
                 this person has *ever* been linked to (open or closed)

        The "same person" is identified by ``national_id``.
        """
        from cases.models import CaseStatus  # avoid circular import

        if not self.national_id:
            # Fallback for suspects without a national-ID on record —
            # use only the current row.
            return self.days_wanted * self.case.crime_level

        related = Suspect.objects.filter(
            national_id=self.national_id,
        ).select_related("case")

        max_days = 0
        max_degree = 0
        for record in related:
            # Lj: only open cases
            if record.case.is_open:
                max_days = max(max_days, record.days_wanted)
            # Di: ALL cases (open or closed)
            max_degree = max(max_degree, record.case.crime_level)

        return max_days * max_degree

    @property
    def reward_amount(self) -> int:
        """
        Bounty reward for information leading to this suspect (Rials).

        Formula (project-doc §4.7 Note 2)::

            reward = most_wanted_score × REWARD_MULTIPLIER

        The multiplier is defined in ``core.constants.REWARD_MULTIPLIER``
        (currently 20,000,000 Rials).  Delegates to
        ``RewardCalculatorService.compute_reward``.
        """
        from core.services import RewardCalculatorService

        return RewardCalculatorService.compute_reward(self.most_wanted_score)


class Warrant(TimeStampedModel):
    """
    Arrest warrant issued by a Sergeant for a suspect (project-doc §4.4).

    A warrant authorises the arrest of a suspect.  It is linked to a
    specific suspect record and issued by a Sergeant.
    """

    class WarrantStatus(models.TextChoices):
        """Lifecycle status of an arrest warrant."""

        ACTIVE = "active", "Active"
        EXECUTED = "executed", "Executed"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    class PriorityChoices(models.TextChoices):
        """Urgency level of an arrest warrant."""

        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    suspect = models.ForeignKey(
        Suspect,
        on_delete=models.CASCADE,
        related_name="warrants",
        verbose_name="Suspect",
    )
    reason = models.TextField(
        verbose_name="Reason for Warrant",
        help_text="Justification for issuing the arrest warrant.",
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issued_warrants",
        verbose_name="Issued By (Sergeant)",
    )
    issued_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Issued At",
    )
    status = models.CharField(
        max_length=20,
        choices=WarrantStatus.choices,
        default=WarrantStatus.ACTIVE,
        verbose_name="Status",
        db_index=True,
    )
    priority = models.CharField(
        max_length=10,
        choices=PriorityChoices.choices,
        default=PriorityChoices.NORMAL,
        verbose_name="Priority",
        db_index=True,
    )

    class Meta:
        verbose_name = "Warrant"
        verbose_name_plural = "Warrants"
        ordering = ["-issued_at"]
        permissions = [
            (SuspectsPerms.CAN_ISSUE_ARREST_WARRANT,
             "Can issue arrest warrant (Sergeant)"),
        ]

    def __str__(self):
        return (
            f"Warrant for {self.suspect.full_name} "
            f"— {self.get_status_display()}"
        )


class Interrogation(TimeStampedModel):
    """
    Records the joint interrogation of a suspect by the Detective and
    Sergeant after arrest (project-doc §4.5).

    Both officers assign a *guilt probability* from 1 (lowest) to 10
    (highest).  These scores are forwarded to the Captain for the final
    decision.
    """

    suspect = models.ForeignKey(
        Suspect,
        on_delete=models.CASCADE,
        related_name="interrogations",
        verbose_name="Suspect",
    )
    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="interrogations",
        verbose_name="Case",
    )
    detective = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="detective_interrogations",
        verbose_name="Detective",
    )
    sergeant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sergeant_interrogations",
        verbose_name="Sergeant",
    )
    detective_guilt_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="Detective's Guilt Score (1–10)",
    )
    sergeant_guilt_score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name="Sergeant's Guilt Score (1–10)",
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Interrogation Notes",
    )

    class Meta:
        verbose_name = "Interrogation"
        verbose_name_plural = "Interrogations"
        ordering = ["-created_at"]
        permissions = [
            (SuspectsPerms.CAN_CONDUCT_INTERROGATION, "Can conduct interrogation session"),
            (SuspectsPerms.CAN_SCORE_GUILT, "Can assign guilt probability score (1-10)"),
        ]

    def __str__(self):
        return (
            f"Interrogation of {self.suspect.full_name} "
            f"— Case #{self.case_id}"
        )


class Trial(TimeStampedModel):
    """
    Court trial and verdict for a suspect (project-doc §4.6).

    The Judge has access to the entire case file, evidence, and all
    involved police members.  If found guilty, a punishment title +
    description is recorded.
    """

    suspect = models.ForeignKey(
        Suspect,
        on_delete=models.CASCADE,
        related_name="trials",
        verbose_name="Suspect",
    )
    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="trials",
        verbose_name="Case",
    )
    judge = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="judged_trials",
        verbose_name="Judge",
    )
    verdict = models.CharField(
        max_length=10,
        choices=VerdictChoice.choices,
        verbose_name="Verdict",
    )
    punishment_title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Punishment Title",
    )
    punishment_description = models.TextField(
        blank=True,
        default="",
        verbose_name="Punishment Description",
    )

    class Meta:
        verbose_name = "Trial"
        verbose_name_plural = "Trials"
        ordering = ["-created_at"]
        permissions = [
            (SuspectsPerms.CAN_RENDER_VERDICT, "Can give final guilty/innocent verdict (Captain/Chief)"),
            (SuspectsPerms.CAN_JUDGE_TRIAL, "Can preside over trial and record punishment (Judge)"),
        ]

    def __str__(self):
        return (
            f"Trial of {self.suspect.full_name} — "
            f"{self.get_verdict_display()}"
        )


class BountyTip(TimeStampedModel):
    """
    Information submitted by a normal user about a suspect or case
    (project-doc §4.8).

    Workflow:
        1. Citizen submits information  → status = PENDING
        2. Police Officer reviews       → OFFICER_REVIEWED or REJECTED
        3. Detective verifies           → VERIFIED → unique_code generated
        4. Citizen presents unique_code at the station to claim the reward.
    """

    suspect = models.ForeignKey(
        Suspect,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bounty_tips",
        verbose_name="Suspect",
    )
    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bounty_tips",
        verbose_name="Case",
    )
    informant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_tips",
        verbose_name="Informant",
    )
    information = models.TextField(
        verbose_name="Submitted Information",
    )

    # ── Review pipeline ─────────────────────────────────────────────
    status = models.CharField(
        max_length=20,
        choices=BountyTipStatus.choices,
        default=BountyTipStatus.PENDING,
        verbose_name="Status",
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="officer_reviewed_tips",
        verbose_name="Reviewed By (Officer)",
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detective_verified_tips",
        verbose_name="Verified By (Detective)",
    )

    # ── Reward ──────────────────────────────────────────────────────
    unique_code = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Reward Claim Code",
        help_text="Generated upon detective verification.",
    )
    reward_amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="Reward Amount (Rials)",
    )
    is_claimed = models.BooleanField(
        default=False,
        verbose_name="Reward Claimed",
    )

    class Meta:
        verbose_name = "Bounty Tip"
        verbose_name_plural = "Bounty Tips"
        ordering = ["-created_at"]
        permissions = [
            (SuspectsPerms.CAN_REVIEW_BOUNTY_TIP, "Can do initial review of bounty tips (Officer)"),
            (SuspectsPerms.CAN_VERIFY_BOUNTY_TIP, "Can verify bounty tip information (Detective)"),
        ]

    def __str__(self):
        return f"Tip #{self.pk} by {self.informant} — {self.get_status_display()}"

    def generate_unique_code(self):
        """
        Generate and assign a unique reward-claim code.  Called when the
        detective verifies the tip.
        """
        self.unique_code = uuid.uuid4().hex[:12].upper()
        self.save(update_fields=["unique_code"])


class SuspectStatusLog(TimeStampedModel):
    """
    Immutable audit trail of every status transition for a suspect.

    Mirrors the ``CaseStatusLog`` pattern from the cases app.
    Stores the previous/new status, who made the change, and an
    optional notes field.
    """

    suspect = models.ForeignKey(
        Suspect,
        on_delete=models.CASCADE,
        related_name="status_logs",
        verbose_name="Suspect",
    )
    from_status = models.CharField(
        max_length=30,
        choices=SuspectStatus.choices,
        verbose_name="Previous Status",
    )
    to_status = models.CharField(
        max_length=30,
        choices=SuspectStatus.choices,
        verbose_name="New Status",
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="suspect_status_changes",
        verbose_name="Changed By",
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Notes / Reason",
    )

    class Meta:
        verbose_name = "Suspect Status Log"
        verbose_name_plural = "Suspect Status Logs"
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Suspect #{self.suspect_id}: "
            f"{self.from_status} → {self.to_status}"
        )


class Bail(TimeStampedModel):
    """
    Bail / fine payment for a suspect (project-doc §4.9, optional).

    Only applicable to Level 2 / Level 3 suspects and Level 3 convicted
    criminals.  The amount is decided by the Sergeant and must be paid
    via a payment gateway.
    """

    suspect = models.ForeignKey(
        Suspect,
        on_delete=models.CASCADE,
        related_name="bails",
        verbose_name="Suspect",
    )
    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="bails",
        verbose_name="Case",
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        verbose_name="Bail Amount (Rials)",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_bails",
        verbose_name="Approved By (Sergeant)",
    )
    conditions = models.TextField(
        blank=True,
        default="",
        verbose_name="Bail Conditions",
        help_text="Optional conditions imposed on the bail release.",
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name="Paid",
    )
    payment_reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Payment Reference",
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Payment Date",
    )

    class Meta:
        verbose_name = "Bail"
        verbose_name_plural = "Bails"
        ordering = ["-created_at"]
        permissions = [
            (SuspectsPerms.CAN_SET_BAIL_AMOUNT, "Can determine bail/fine amount (Sergeant)"),
        ]

    def __str__(self):
        status = "Paid" if self.is_paid else "Unpaid"
        return f"Bail for {self.suspect.full_name} — {status}"
