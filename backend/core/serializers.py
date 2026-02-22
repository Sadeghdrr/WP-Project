"""
Core app serializers.

**Response-only** serializers for the aggregated endpoints served by the
core app.  These serializers define the *output schema* for the dashboard,
global search, and system constants views.  They do **not** accept input
data; all filtering is handled via query parameters validated in the
service layer.

Architectural note
------------------
These serializers never import models from other apps directly at the
module level.  They work exclusively with plain Python dicts / lists
produced by the service layer, keeping the core app decoupled from
concrete model implementations in ``cases``, ``suspects``, ``evidence``,
and ``accounts``.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers


# ════════════════════════════════════════════════════════════════════
#  Dashboard Statistics
# ════════════════════════════════════════════════════════════════════

class CasesByStatusSerializer(serializers.Serializer):
    """
    Breakdown of case counts grouped by status.

    Example::

        {"status": "open", "label": "Open", "count": 12}
    """

    status = serializers.CharField(
        help_text="Machine-readable status key (e.g. 'open', 'closed').",
    )
    label = serializers.CharField(
        help_text="Human-readable display label for the status.",
    )
    count = serializers.IntegerField(
        help_text="Number of cases currently in this status.",
    )


class CasesByCrimeLevelSerializer(serializers.Serializer):
    """
    Breakdown of case counts grouped by crime level.

    Example::

        {"crime_level": 4, "label": "Critical", "count": 3}
    """

    crime_level = serializers.IntegerField(
        help_text="Integer crime-level value (1–4).",
    )
    label = serializers.CharField(
        help_text="Human-readable label for the crime level.",
    )
    count = serializers.IntegerField(
        help_text="Number of cases at this crime level.",
    )


class TopWantedSuspectSerializer(serializers.Serializer):
    """
    Abbreviated suspect info for the dashboard's "Top Wanted" widget.

    Example::

        {
            "id": 42,
            "full_name": "John Doe",
            "national_id": "1234567890",
            "photo_url": "/media/suspect_photos/2025/01/john.jpg",
            "most_wanted_score": 120,
            "reward_amount": 1200000000,
            "days_wanted": 45,
            "case_id": 7,
            "case_title": "Downtown Heist"
        }
    """

    id = serializers.IntegerField(help_text="Suspect record PK.")
    full_name = serializers.CharField(help_text="Suspect's full name.")
    national_id = serializers.CharField(
        help_text="National ID (used for cross-case grouping).",
        allow_blank=True,
    )
    photo_url = serializers.CharField(
        help_text="Absolute or relative URL to suspect photo.",
        allow_null=True,
        allow_blank=True,
    )
    most_wanted_score = serializers.IntegerField(
        help_text="Ranking score: max(days_wanted) × max(crime_degree).",
    )
    reward_amount = serializers.IntegerField(
        help_text="Bounty reward in Rials.",
    )
    days_wanted = serializers.IntegerField(
        help_text="Number of days the suspect has been wanted.",
    )
    case_id = serializers.IntegerField(help_text="Primary case PK.")
    case_title = serializers.CharField(help_text="Primary case title.")


class RecentActivitySerializer(serializers.Serializer):
    """
    A single recent activity item for the dashboard feed.

    Example::

        {
            "timestamp": "2025-06-15T10:30:00Z",
            "type": "case_status_change",
            "description": "Case #12 moved to Investigation",
            "actor": "det.smith"
        }
    """

    timestamp = serializers.DateTimeField(
        help_text="When the activity occurred.",
    )
    type = serializers.CharField(
        help_text=(
            "Activity category, e.g. 'case_created', 'evidence_added', "
            "'suspect_identified', 'case_status_change'."
        ),
    )
    description = serializers.CharField(
        help_text="Human-readable description of the activity.",
    )
    actor = serializers.CharField(
        help_text="Username of the user who performed the action.",
        allow_null=True,
        allow_blank=True,
    )


class DashboardStatsSerializer(serializers.Serializer):
    """
    Top-level response serializer for ``GET /api/core/dashboard/``.

    Returns an aggregated snapshot of system metrics.  The data returned
    is **role-aware**:

    * **Captain / Police Chief / System Admin**: department-wide stats.
    * **Detective**: stats scoped to their own assigned cases.
    * **Sergeant**: stats scoped to their supervised cases.
    * **Other roles**: limited public statistics only.

    Response shape::

        {
            "total_cases": 150,
            "active_cases": 42,
            "closed_cases": 95,
            "voided_cases": 13,
            "total_suspects": 87,
            "total_evidence": 320,
            "total_employees": 55,
            "unassigned_evidence_count": 12,
            "cases_by_status": [...],
            "cases_by_crime_level": [...],
            "top_wanted_suspects": [...],
            "recent_activity": [...]
        }
    """

    # ── Scalar counters ──────────────────────────────────────────────
    total_cases = serializers.IntegerField(
        help_text="Total number of cases (scoped by role).",
    )
    active_cases = serializers.IntegerField(
        help_text="Cases that are currently open / under investigation.",
    )
    closed_cases = serializers.IntegerField(
        help_text="Cases that have been closed.",
    )
    voided_cases = serializers.IntegerField(
        help_text="Cases that were voided (3 complaint rejections).",
    )
    total_suspects = serializers.IntegerField(
        help_text="Total suspect records (scoped by role).",
    )
    total_evidence = serializers.IntegerField(
        help_text="Total evidence items (scoped by role).",
    )
    total_employees = serializers.IntegerField(
        help_text="Total number of organisation employees (staff users).",
    )
    unassigned_evidence_count = serializers.IntegerField(
        help_text=(
            "Evidence items not yet linked to a detective's board or "
            "whose case has no assigned detective."
        ),
    )

    # ── Nested breakdowns ────────────────────────────────────────────
    cases_by_status = CasesByStatusSerializer(
        many=True,
        help_text="Case count grouped by workflow status.",
    )
    cases_by_crime_level = CasesByCrimeLevelSerializer(
        many=True,
        help_text="Case count grouped by crime level.",
    )
    top_wanted_suspects = TopWantedSuspectSerializer(
        many=True,
        help_text="Top N most-wanted suspects ordered by score descending.",
    )
    recent_activity = RecentActivitySerializer(
        many=True,
        help_text="Latest activity feed items.",
    )


# ════════════════════════════════════════════════════════════════════
#  Global Search
# ════════════════════════════════════════════════════════════════════

class SearchCaseResultSerializer(serializers.Serializer):
    """
    A single case hit from the global search.

    Example::

        {
            "id": 7,
            "title": "Downtown Heist",
            "status": "investigation",
            "crime_level": 2,
            "crime_level_label": "Level 2 (Medium)",
            "created_at": "2025-05-01T09:00:00Z"
        }
    """

    id = serializers.IntegerField(help_text="Case PK.")
    title = serializers.CharField(help_text="Case title.")
    status = serializers.CharField(help_text="Current workflow status key.")
    crime_level = serializers.IntegerField(help_text="Crime level (1–4).")
    crime_level_label = serializers.CharField(
        help_text="Human-readable crime level label.",
    )
    created_at = serializers.DateTimeField(help_text="Case creation timestamp.")


class SearchSuspectResultSerializer(serializers.Serializer):
    """
    A single suspect hit from the global search.

    Example::

        {
            "id": 42,
            "full_name": "John Doe",
            "national_id": "1234567890",
            "status": "wanted",
            "case_id": 7,
            "case_title": "Downtown Heist"
        }
    """

    id = serializers.IntegerField(help_text="Suspect record PK.")
    full_name = serializers.CharField(help_text="Suspect's full name.")
    national_id = serializers.CharField(
        help_text="National ID.",
        allow_blank=True,
    )
    status = serializers.CharField(help_text="Current suspect status.")
    case_id = serializers.IntegerField(help_text="Related case PK.")
    case_title = serializers.CharField(help_text="Related case title.")


class SearchEvidenceResultSerializer(serializers.Serializer):
    """
    A single evidence hit from the global search.

    Example::

        {
            "id": 88,
            "title": "Fingerprint on glass",
            "evidence_type": "biological",
            "evidence_type_label": "Biological / Medical",
            "case_id": 7,
            "case_title": "Downtown Heist"
        }
    """

    id = serializers.IntegerField(help_text="Evidence PK.")
    title = serializers.CharField(help_text="Evidence title.")
    evidence_type = serializers.CharField(help_text="Evidence type key.")
    evidence_type_label = serializers.CharField(
        help_text="Human-readable evidence type label.",
    )
    case_id = serializers.IntegerField(help_text="Related case PK.")
    case_title = serializers.CharField(help_text="Related case title.")


class GlobalSearchResponseSerializer(serializers.Serializer):
    """
    Top-level response serializer for ``GET /api/core/search/?q=...``.

    Returns a unified, categorised JSON response containing matched
    results across Cases, Suspects, and Evidence.  Each category is a
    list that may be empty if no matches were found.

    Query parameter:
        ``q`` (str, required) — The search term (min 2 characters).

    Optional query parameters:
        ``category`` (str) — Restrict search to ``cases``, ``suspects``,
            or ``evidence``.  Omit to search all categories.
        ``limit`` (int) — Max results per category (default 10, max 50).

    Response shape::

        {
            "query": "john",
            "total_results": 15,
            "cases": [...],
            "suspects": [...],
            "evidence": [...]
        }
    """

    query = serializers.CharField(
        help_text="The search term that was used.",
    )
    total_results = serializers.IntegerField(
        help_text="Sum of results across all categories.",
    )
    cases = SearchCaseResultSerializer(
        many=True,
        help_text="Case records matching the search query.",
    )
    suspects = SearchSuspectResultSerializer(
        many=True,
        help_text="Suspect records matching the search query.",
    )
    evidence = SearchEvidenceResultSerializer(
        many=True,
        help_text="Evidence records matching the search query.",
    )


# ════════════════════════════════════════════════════════════════════
#  System Constants / Enums
# ════════════════════════════════════════════════════════════════════

class ChoiceItemSerializer(serializers.Serializer):
    """
    A single key-label pair representing one choice/enum option.

    Example::

        {"value": "open", "label": "Open"}
    """

    value = serializers.CharField(
        help_text="Machine-readable value to send in API requests.",
    )
    label = serializers.CharField(
        help_text="Human-readable display label for the UI.",
    )


class RoleHierarchyItemSerializer(serializers.Serializer):
    """
    A single role with its hierarchy level for the frontend's
    understanding of organisational structure.

    Example::

        {"id": 3, "name": "Captain", "hierarchy_level": 8}
    """

    id = serializers.IntegerField(help_text="Role PK.")
    name = serializers.CharField(help_text="Role display name.")
    hierarchy_level = serializers.IntegerField(
        help_text="Authority level (higher = more authority).",
    )


class SystemConstantsSerializer(serializers.Serializer):
    """
    Top-level response serializer for ``GET /api/core/constants/``.

    Provides all system-wide choice enumerations so the frontend can
    dynamically build dropdowns, filters, and labels **without**
    hardcoding values.

    Response shape::

        {
            "crime_levels": [
                {"value": "1", "label": "Level 3 (Minor)"},
                ...
            ],
            "case_statuses": [...],
            "case_creation_types": [...],
            "evidence_types": [...],
            "evidence_file_types": [...],
            "suspect_statuses": [...],
            "verdict_choices": [...],
            "bounty_tip_statuses": [...],
            "complainant_statuses": [...],
            "role_hierarchy": [
                {"id": 1, "name": "Police Chief", "hierarchy_level": 10},
                ...
            ]
        }
    """

    crime_levels = ChoiceItemSerializer(
        many=True,
        help_text="Available crime severity levels (CrimeLevel enum).",
    )
    case_statuses = ChoiceItemSerializer(
        many=True,
        help_text="All possible case workflow statuses (CaseStatus enum).",
    )
    case_creation_types = ChoiceItemSerializer(
        many=True,
        help_text="How a case can be created (complaint vs crime-scene).",
    )
    evidence_types = ChoiceItemSerializer(
        many=True,
        help_text="Evidence type discriminator choices (EvidenceType enum).",
    )
    evidence_file_types = ChoiceItemSerializer(
        many=True,
        help_text="Allowed file media types for evidence attachments.",
    )
    suspect_statuses = ChoiceItemSerializer(
        many=True,
        help_text="Suspect lifecycle statuses (SuspectStatus enum).",
    )
    verdict_choices = ChoiceItemSerializer(
        many=True,
        help_text="Judge verdict options (Guilty / Innocent).",
    )
    bounty_tip_statuses = ChoiceItemSerializer(
        many=True,
        help_text="Bounty tip review pipeline statuses.",
    )
    complainant_statuses = ChoiceItemSerializer(
        many=True,
        help_text="Approval statuses for case complainants.",
    )
    role_hierarchy = RoleHierarchyItemSerializer(
        many=True,
        help_text="All roles with their hierarchy levels, ordered by authority.",
    )


# ════════════════════════════════════════════════════════════════════
#  Notifications
# ════════════════════════════════════════════════════════════════════

class NotificationSerializer(serializers.Serializer):
    """
    Read-only serializer for ``Notification`` instances.

    Used by the Notification ViewSet to list and retrieve notifications
    for the authenticated user.
    """

    id = serializers.IntegerField(read_only=True, help_text="Notification PK.")
    title = serializers.CharField(
        read_only=True,
        help_text="Short notification title.",
    )
    message = serializers.CharField(
        read_only=True,
        help_text="Full notification message body.",
    )
    is_read = serializers.BooleanField(
        read_only=True,
        help_text="Whether the recipient has marked this notification as read.",
    )
    created_at = serializers.DateTimeField(
        read_only=True,
        help_text="When the notification was created.",
    )
    content_type = serializers.StringRelatedField(
        read_only=True,
        help_text="Related content type (if any).",
    )
    object_id = serializers.IntegerField(
        read_only=True,
        allow_null=True,
        help_text="PK of the related object (if any).",
    )
