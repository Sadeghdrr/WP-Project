"""
Evidence app Service Layer.

This module is the **single source of truth** for all business logic
in the ``evidence`` app.  Views must remain thin: validate input via
serializers, call a service method, and return the result wrapped in
a DRF ``Response``.

Architecture
------------
- ``EvidenceQueryService``      — Filtered queryset construction & retrieval.
- ``EvidenceProcessingService`` — Polymorphic evidence creation, update, delete.
- ``MedicalExaminerService``    — Coroner verification workflow for biological evidence.
- ``EvidenceFileService``       — File attachment management.
- ``ChainOfCustodyService``     — Read-only audit trail assembly.

Permission Constants (from ``core.permissions_constants.EvidencePerms``)
------------------------------------------------------------------------
- ``ADD_EVIDENCE``               — Create any evidence type.
- ``CHANGE_EVIDENCE``            — Update evidence metadata.
- ``DELETE_EVIDENCE``            — Delete evidence.
- ``VIEW_EVIDENCE``              — Read evidence records.
- ``CAN_VERIFY_EVIDENCE``        — Coroner verifies biological evidence.
- ``CAN_REGISTER_FORENSIC_RESULT`` — Coroner fills in forensic result.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet

from core.domain.access import apply_role_filter, get_user_role_name, ScopeConfig
from core.domain.exceptions import DomainError, NotFound, PermissionDenied
from core.domain.notifications import NotificationService
from core.permissions_constants import EvidencePerms

from .models import (
    BiologicalEvidence,
    Evidence,
    EvidenceFile,
    EvidenceType,
    IdentityEvidence,
    TestimonyEvidence,
    VehicleEvidence,
)

logger = logging.getLogger(__name__)

# ── Role-scoped queryset configuration for evidence visibility ──────
_EVIDENCE_SCOPE_CONFIG: ScopeConfig = {
    # Unrestricted roles
    "system_admin": lambda qs, u: qs,
    "police_chief": lambda qs, u: qs,
    "captain": lambda qs, u: qs,
    "judge": lambda qs, u: qs,
    # Detective sees evidence on their assigned cases
    "detective": lambda qs, u: qs.filter(case__assigned_detective=u),
    # Sergeant sees evidence on cases they supervise
    "sergeant": lambda qs, u: qs.filter(case__assigned_sergeant=u),
    # Coroner sees all biological evidence plus evidence on cases they examine
    "coroner": lambda qs, u: qs.filter(
        Q(evidence_type=EvidenceType.BIOLOGICAL)
        | Q(case__assigned_detective=u)
    ),
    # Cadet sees evidence on cases currently in their review queue
    "cadet": lambda qs, u: qs.filter(case__created_by=u),
    # Police Officer / Patrol Officer
    "police_officer": lambda qs, u: qs.filter(case__created_by=u),
    "patrol_officer": lambda qs, u: qs.filter(case__created_by=u),
    # Complainant / Witness see evidence only on their associated cases
    "complainant": lambda qs, u: qs.filter(
        Q(case__complainants__user=u) | Q(case__created_by=u)
    ).distinct(),
    "witness": lambda qs, u: qs.filter(case__witnesses__user=u).distinct(),
    # Base User — minimal visibility
    "base_user": lambda qs, u: qs.filter(case__created_by=u),
}


# ═══════════════════════════════════════════════════════════════════
#  Evidence Query Service
# ═══════════════════════════════════════════════════════════════════


class EvidenceQueryService:
    """
    Constructs filtered, annotated querysets for listing evidence.

    All heavy query concerns (filter assembly, annotation, ordering)
    live here so the view stays thin.
    """

    @staticmethod
    def get_filtered_queryset(
        requesting_user: Any,
        filters: dict[str, Any],
    ) -> QuerySet[Evidence]:
        """
        Build a role-scoped, filtered queryset of ``Evidence`` objects.
        """
        # 1. Start with all evidence, apply role-based scoping
        qs = Evidence.objects.all()
        qs = apply_role_filter(
            qs,
            requesting_user,
            scope_config=_EVIDENCE_SCOPE_CONFIG,
            default="none",
        )

        # 2. Apply explicit filters
        evidence_type = filters.get("evidence_type")
        if evidence_type:
            qs = qs.filter(evidence_type=evidence_type)

        case_id = filters.get("case")
        if case_id is not None:
            qs = qs.filter(case_id=case_id)

        registered_by = filters.get("registered_by")
        if registered_by is not None:
            qs = qs.filter(registered_by_id=registered_by)

        is_verified = filters.get("is_verified")
        if is_verified is not None:
            qs = qs.filter(biologicalevidence__is_verified=is_verified)

        search = filters.get("search")
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )

        created_after = filters.get("created_after")
        if created_after is not None:
            qs = qs.filter(created_at__date__gte=created_after)

        created_before = filters.get("created_before")
        if created_before is not None:
            qs = qs.filter(created_at__date__lte=created_before)

        # 3. Optimise with select_related / prefetch_related
        qs = qs.select_related("registered_by", "case").prefetch_related("files")

        return qs

    @staticmethod
    def get_evidence_detail(pk: int) -> Evidence:
        """
        Retrieve a single evidence item by PK, resolved to its most
        specific child type with all related data pre-fetched.

        Raises ``NotFound`` if no evidence with the given PK exists.
        """
        try:
            evidence = (
                Evidence.objects
                .select_related("registered_by", "case")
                .prefetch_related("files")
                .get(pk=pk)
            )
        except Evidence.DoesNotExist:
            raise NotFound(f"Evidence with id {pk} not found.")

        # Resolve to the most specific child type
        child_accessors = [
            "testimonyevidence",
            "biologicalevidence",
            "vehicleevidence",
            "identityevidence",
        ]
        for accessor in child_accessors:
            try:
                child = getattr(evidence, accessor)
                # Re-attach prefetched caches to avoid extra queries
                child._prefetched_objects_cache = getattr(
                    evidence, "_prefetched_objects_cache", {}
                )
                return child
            except (Evidence.DoesNotExist, AttributeError,
                    TestimonyEvidence.DoesNotExist,
                    BiologicalEvidence.DoesNotExist,
                    VehicleEvidence.DoesNotExist,
                    IdentityEvidence.DoesNotExist):
                continue

        # No child found — it's an "Other" type
        return evidence


# ═══════════════════════════════════════════════════════════════════
#  Evidence Processing Service
# ═══════════════════════════════════════════════════════════════════


class EvidenceProcessingService:
    """
    Handles polymorphic evidence creation, updates, and deletion.

    The single ``process_new_evidence`` entry point accepts a validated
    payload (from any of the type-specific create serializers) plus the
    ``evidence_type`` discriminator and delegates to the appropriate
    model creation method.
    """

    #: Maps ``EvidenceType`` values to their corresponding model classes.
    _MODEL_MAP: dict[str, type[Evidence]] = {
        EvidenceType.TESTIMONY: TestimonyEvidence,
        EvidenceType.BIOLOGICAL: BiologicalEvidence,
        EvidenceType.VEHICLE: VehicleEvidence,
        EvidenceType.IDENTITY: IdentityEvidence,
        EvidenceType.OTHER: Evidence,
    }

    # ── Type-specific validation methods ─────────────────────────────

    @staticmethod
    def _validate_vehicle(data: dict[str, Any]) -> None:
        """Enforce license_plate XOR serial_number."""
        plate = data.get("license_plate", "").strip()
        serial = data.get("serial_number", "").strip()
        has_plate = bool(plate)
        has_serial = bool(serial)
        if has_plate and has_serial:
            raise DomainError(
                "Provide either a license plate or a serial number, not both."
            )
        if not has_plate and not has_serial:
            raise DomainError(
                "Either a license plate or a serial number must be provided."
            )

    @staticmethod
    def _validate_biological(data: dict[str, Any]) -> None:
        """Ensure forensic_result is empty on creation (pending verification)."""
        if data.get("forensic_result", "").strip():
            raise DomainError(
                "Forensic result must be empty on creation. "
                "It will be filled by the Coroner during verification."
            )

    @staticmethod
    def _validate_testimony(data: dict[str, Any]) -> None:
        """Require statement_text (transcript)."""
        statement = data.get("statement_text", "").strip()
        if not statement:
            raise DomainError(
                "A transcript (statement_text) is required for testimony evidence."
            )

    @staticmethod
    def _validate_identity(data: dict[str, Any]) -> None:
        """Require owner_full_name."""
        owner = data.get("owner_full_name", "").strip()
        if not owner:
            raise DomainError(
                "Owner's full name (owner_full_name) is required for identity-document evidence."
            )
        # Validate document_details if present
        details = data.get("document_details")
        if details is not None:
            if not isinstance(details, dict):
                raise DomainError("document_details must be a JSON object (dict).")
            for k, v in details.items():
                if not isinstance(k, str) or not isinstance(v, str):
                    raise DomainError(
                        "All keys and values in document_details must be strings."
                    )

    #: Maps evidence_type to its type-specific validator
    _VALIDATORS: dict[str, Any] = {
        EvidenceType.VEHICLE: _validate_vehicle.__func__,
        EvidenceType.BIOLOGICAL: _validate_biological.__func__,
        EvidenceType.TESTIMONY: _validate_testimony.__func__,
        EvidenceType.IDENTITY: _validate_identity.__func__,
    }

    @staticmethod
    @transaction.atomic
    def process_new_evidence(
        evidence_type: str,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Evidence:
        """
        Create a new evidence item of the specified type.
        """
        # 1. Permission check
        if not requesting_user.has_perm(f"evidence.{EvidencePerms.ADD_EVIDENCE}"):
            raise PermissionDenied("You do not have permission to add evidence.")

        # 2. Validate evidence_type
        valid_types = {choice[0] for choice in EvidenceType.choices}
        if evidence_type not in valid_types:
            raise DomainError(f"Invalid evidence type: {evidence_type}")

        # 3. Run type-specific validation
        validator = EvidenceProcessingService._VALIDATORS.get(evidence_type)
        if validator:
            validator(validated_data)

        # 4. Resolve model class
        model_cls = EvidenceProcessingService._MODEL_MAP[evidence_type]

        # 5. Inject registered_by
        validated_data["registered_by"] = requesting_user

        # 6. For "other" type, explicitly set evidence_type
        #    (child models set it in their save() method)
        if evidence_type == EvidenceType.OTHER:
            validated_data["evidence_type"] = EvidenceType.OTHER

        # 7. Create the evidence instance
        evidence = model_cls.objects.create(**validated_data)

        # 8. Dispatch notification to the case's assigned detective
        case = evidence.case
        if hasattr(case, "assigned_detective") and case.assigned_detective:
            NotificationService.create(
                actor=requesting_user,
                recipients=case.assigned_detective,
                event_type="evidence_added",
                payload={
                    "case_id": case.id,
                    "evidence_id": evidence.id,
                    "evidence_type": evidence_type,
                },
                related_object=evidence,
            )

        logger.info(
            "Evidence #%d (%s) created for Case #%d by user %s",
            evidence.pk,
            evidence_type,
            case.pk,
            requesting_user,
        )
        return evidence

    @staticmethod
    @transaction.atomic
    def update_evidence(
        evidence: Evidence,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> Evidence:
        """
        Update an existing evidence item's mutable fields.
        """
        # 1. Permission check
        if not requesting_user.has_perm(f"evidence.{EvidencePerms.CHANGE_EVIDENCE}"):
            raise PermissionDenied("You do not have permission to update evidence.")

        # 2. Apply type-specific validation for vehicle updates
        if evidence.evidence_type == EvidenceType.VEHICLE:
            # Merge incoming data with existing values for XOR check
            merged = {}
            merged["license_plate"] = validated_data.get(
                "license_plate", evidence.license_plate
            )
            merged["serial_number"] = validated_data.get(
                "serial_number", evidence.serial_number
            )
            EvidenceProcessingService._validate_vehicle(merged)

        # 3. Set each field on the instance
        update_fields = []
        for key, value in validated_data.items():
            setattr(evidence, key, value)
            update_fields.append(key)

        # 4. Always include updated_at
        if update_fields:
            update_fields.append("updated_at")
            evidence.save(update_fields=update_fields)

        logger.info(
            "Evidence #%d updated by user %s (fields: %s)",
            evidence.pk,
            requesting_user,
            ", ".join(update_fields),
        )
        return evidence

    @staticmethod
    @transaction.atomic
    def delete_evidence(
        evidence: Evidence,
        requesting_user: Any,
    ) -> None:
        """
        Delete an evidence item permanently.
        """
        # 1. Permission check
        if not requesting_user.has_perm(f"evidence.{EvidencePerms.DELETE_EVIDENCE}"):
            raise PermissionDenied("You do not have permission to delete evidence.")

        # 2. Guard: verified biological evidence cannot be deleted (unless admin)
        if evidence.evidence_type == EvidenceType.BIOLOGICAL:
            try:
                bio = evidence.biologicalevidence
                if bio.is_verified and not requesting_user.is_superuser:
                    raise DomainError(
                        "Verified biological evidence cannot be deleted "
                        "without admin privileges."
                    )
            except BiologicalEvidence.DoesNotExist:
                pass

        evidence_pk = evidence.pk
        evidence.delete()

        logger.info(
            "Evidence #%d deleted by user %s",
            evidence_pk,
            requesting_user,
        )

    @staticmethod
    @transaction.atomic
    def link_evidence_to_case(
        evidence: Evidence,
        case_id: int,
        requesting_user: Any,
    ) -> Evidence:
        """
        Link an existing evidence item to a (different) case.
        """
        # 1. Permission check
        if not requesting_user.has_perm(f"evidence.{EvidencePerms.CHANGE_EVIDENCE}"):
            raise PermissionDenied("You do not have permission to re-link evidence.")

        # 2. Fetch target case
        from cases.models import Case

        try:
            target_case = Case.objects.get(pk=case_id)
        except Case.DoesNotExist:
            raise DomainError(f"Case with id {case_id} does not exist.")

        # 3. Update FK
        evidence.case = target_case
        evidence.save(update_fields=["case_id", "updated_at"])

        logger.info(
            "Evidence #%d linked to Case #%d by user %s",
            evidence.pk,
            case_id,
            requesting_user,
        )
        return evidence

    @staticmethod
    @transaction.atomic
    def unlink_evidence_from_case(
        evidence: Evidence,
        case_id: int,
        requesting_user: Any,
    ) -> Evidence:
        """
        Unlink evidence from the specified case.

        Since the FK is non-nullable, unlinking without a replacement
        is not allowed.
        """
        # 1. Permission check
        if not requesting_user.has_perm(f"evidence.{EvidencePerms.CHANGE_EVIDENCE}"):
            raise PermissionDenied("You do not have permission to unlink evidence.")

        # 2. Verify the evidence belongs to the specified case
        if evidence.case_id != case_id:
            raise DomainError(
                f"Evidence #{evidence.pk} is not linked to Case #{case_id}."
            )

        # 3. FK is non-nullable — cannot unlink without replacement
        raise DomainError(
            "Evidence must be linked to a case. "
            "Use link-case to reassign instead."
        )



# ═══════════════════════════════════════════════════════════════════
#  Medical Examiner (Coroner) Service
# ═══════════════════════════════════════════════════════════════════


class MedicalExaminerService:
    """
    Handles the Coroner verification workflow for **biological / medical**
    evidence items.
    """

    @staticmethod
    @transaction.atomic
    def verify_biological_evidence(
        evidence_id: int,
        examiner_user: Any,
        decision: str,
        forensic_result: str = "",
        notes: str = "",
    ) -> BiologicalEvidence:
        """
        Coroner approves or rejects a piece of biological evidence.
        """
        # 1. Permission check
        if not examiner_user.has_perm(f"evidence.{EvidencePerms.CAN_VERIFY_EVIDENCE}"):
            raise PermissionDenied("Only the Coroner can verify biological evidence.")

        # 2. Fetch evidence
        try:
            bio_evidence = (
                BiologicalEvidence.objects
                .select_related("case", "registered_by")
                .get(pk=evidence_id)
            )
        except BiologicalEvidence.DoesNotExist:
            raise NotFound(f"Biological evidence with id {evidence_id} not found.")

        # 3. Idempotency guard
        if bio_evidence.is_verified:
            raise DomainError("This evidence has already been verified.")

        # 4. Decision processing
        if decision == "approve":
            if not forensic_result.strip():
                raise DomainError("Forensic result is required when approving.")
            bio_evidence.is_verified = True
            bio_evidence.forensic_result = forensic_result
            bio_evidence.verified_by = examiner_user
        elif decision == "reject":
            if not notes.strip():
                raise DomainError("A rejection reason is required.")
            bio_evidence.is_verified = False
            bio_evidence.forensic_result = f"REJECTED: {notes}"
            bio_evidence.verified_by = examiner_user

        # 5. Save
        bio_evidence.save(update_fields=[
            "is_verified", "forensic_result", "verified_by", "updated_at",
        ])

        # 6. Notify detective
        case = bio_evidence.case
        if hasattr(case, "assigned_detective") and case.assigned_detective:
            event_msg = "approved" if decision == "approve" else "rejected"
            NotificationService.create(
                actor=examiner_user,
                recipients=case.assigned_detective,
                event_type="evidence_added",
                payload={
                    "case_id": case.id,
                    "evidence_id": bio_evidence.id,
                    "verification": event_msg,
                },
                related_object=bio_evidence,
            )

        logger.info(
            "Biological evidence #%d %s by Coroner %s",
            bio_evidence.pk,
            decision,
            examiner_user,
        )
        return bio_evidence

    @staticmethod
    def get_pending_verifications(
        examiner_user: Any,
    ) -> QuerySet[BiologicalEvidence]:
        """
        Return all biological evidence items pending Coroner verification.
        """
        if not examiner_user.has_perm(f"evidence.{EvidencePerms.CAN_VERIFY_EVIDENCE}"):
            raise PermissionDenied("Only the Coroner can view pending verifications.")

        return (
            BiologicalEvidence.objects
            .filter(is_verified=False, verified_by__isnull=True)
            .select_related("case", "registered_by")
            .order_by("-created_at")
        )


# ═══════════════════════════════════════════════════════════════════
#  Evidence File Service
# ═══════════════════════════════════════════════════════════════════


class EvidenceFileService:
    """
    Manages file attachments (images, videos, audio, documents) on
    evidence items.
    """

    @staticmethod
    @transaction.atomic
    def upload_file(
        evidence: Evidence,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> EvidenceFile:
        """Attach a file to an evidence item."""
        if not requesting_user.has_perm(f"evidence.{EvidencePerms.ADD_EVIDENCEFILE}"):
            raise PermissionDenied("You do not have permission to upload evidence files.")

        evidence_file = EvidenceFile.objects.create(
            evidence=evidence, **validated_data
        )
        logger.info(
            "File #%d attached to Evidence #%d by user %s",
            evidence_file.pk,
            evidence.pk,
            requesting_user,
        )
        return evidence_file

    @staticmethod
    def get_files_for_evidence(evidence: Evidence) -> QuerySet[EvidenceFile]:
        """Return all file attachments for a given evidence item."""
        return evidence.files.order_by("-created_at")

    @staticmethod
    @transaction.atomic
    def delete_file(
        evidence_file: EvidenceFile,
        requesting_user: Any,
    ) -> None:
        """Delete a specific file attachment."""
        if not requesting_user.has_perm(f"evidence.{EvidencePerms.DELETE_EVIDENCEFILE}"):
            raise PermissionDenied("You do not have permission to delete evidence files.")

        file_pk = evidence_file.pk
        evidence_file.file.delete(save=False)
        evidence_file.delete()
        logger.info(
            "Evidence file #%d deleted by user %s",
            file_pk,
            requesting_user,
        )


# ═══════════════════════════════════════════════════════════════════
#  Chain of Custody Service
# ═══════════════════════════════════════════════════════════════════


class ChainOfCustodyService:
    """
    Assembles a read-only audit trail for an evidence item.
    """

    @staticmethod
    def get_custody_trail(evidence: Evidence) -> list[dict[str, Any]]:
        """
        Build the full chain-of-custody trail for an evidence item.
        """
        trail: list[dict[str, Any]] = []

        # 1. Registration event
        trail.append({
            "timestamp": evidence.created_at,
            "action": "Registered",
            "performed_by": evidence.registered_by_id,
            "performer_name": evidence.registered_by.get_full_name(),
            "details": f"Evidence registered as {evidence.get_evidence_type_display()}",
        })

        # 2. File upload events
        for f in evidence.files.all().order_by("created_at"):
            trail.append({
                "timestamp": f.created_at,
                "action": "File Added",
                "performed_by": evidence.registered_by_id,
                "performer_name": evidence.registered_by.get_full_name(),
                "details": f"{f.get_file_type_display()}: {f.caption}" if f.caption else f.get_file_type_display(),
            })

        # 3. Verification event (biological only)
        if evidence.evidence_type == EvidenceType.BIOLOGICAL:
            try:
                bio = evidence if isinstance(evidence, BiologicalEvidence) else evidence.biologicalevidence
                if bio.verified_by is not None:
                    action_label = "Verified by Coroner" if bio.is_verified else "Rejected by Coroner"
                    trail.append({
                        "timestamp": bio.updated_at,
                        "action": action_label,
                        "performed_by": bio.verified_by_id,
                        "performer_name": bio.verified_by.get_full_name(),
                        "details": bio.forensic_result or "",
                    })
            except BiologicalEvidence.DoesNotExist:
                pass

        # 4. Sort by timestamp
        trail.sort(key=lambda e: e["timestamp"])

        return trail
