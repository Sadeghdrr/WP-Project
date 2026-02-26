"""
Board app serializers.

Contains all Request and Response serializers for the Detective Board API.
Serializers are responsible for field definitions, read/write constraints,
GenericForeignKey resolution, and basic field-level validation.
**No business logic** lives here — all domain rules are delegated to
``services.py``.

GenericForeignKey Strategy
--------------------------
``BoardItem`` uses Django's ``GenericForeignKey`` to reference heterogeneous
content objects (Cases, Suspects, Evidence sub-types, BoardNotes).  DRF has
no built-in support for this pattern, so we implement a custom
``GenericObjectRelatedField`` that:

1. On **read**: resolves the ``content_type`` + ``object_id`` pair, figures
   out which app/model it belongs to, and serialises a compact summary
   (``type``, ``id``, ``display_name``) plus a ``detail_url`` so the
   frontend can lazily fetch the full object if needed.

2. On **write**: accepts a ``{"content_type_id": <int>, "object_id": <int>}``
   dict (or the string shortcuts ``"suspect:<id>"``, ``"evidence:<id>"``,
   etc.) and validates that the target object actually exists.

This design keeps the board's canvas generic while giving the Next.js
front-end enough information to render the correct pin icon (e.g. a
fingerprint icon for BiologicalEvidence vs. a car icon for VehicleEvidence).
"""

from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from .models import BoardConnection, BoardItem, BoardNote, DetectiveBoard


# ═══════════════════════════════════════════════════════════════════
#  URL-prefix registry for detail_url construction
# ═══════════════════════════════════════════════════════════════════

_DETAIL_URL_MAP: dict[str, str] = {
    "cases.case": "/api/cases/",
    "suspects.suspect": "/api/suspects/",
    "evidence.evidence": "/api/evidence/",
    "evidence.testimonyevidence": "/api/evidence/testimony/",
    "evidence.biologicalevidence": "/api/evidence/biological/",
    "evidence.vehicleevidence": "/api/evidence/vehicle/",
    "evidence.identityevidence": "/api/evidence/identity/",
    "board.boardnote": "/api/boards/notes/",
}


# ═══════════════════════════════════════════════════════════════════
#  Generic Object Field
# ═══════════════════════════════════════════════════════════════════


class GenericObjectRelatedField(serializers.Field):
    """
    Custom DRF field to serialize/deserialize Django ``GenericForeignKey``
    fields on ``BoardItem``.
    """

    # Models that may be pinned to a detective board.
    ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
        [
            "cases.case",
            "suspects.suspect",
            "evidence.evidence",
            "evidence.testimonyevidence",
            "evidence.biologicalevidence",
            "evidence.vehicleevidence",
            "evidence.identityevidence",
            "board.boardnote",
        ]
    )

    def to_representation(self, value: Any) -> dict[str, Any] | None:
        """
        Convert a resolved ``content_object`` into a JSON-serialisable dict.
        """
        # Support the pre-fetched cache set by get_full_board_graph.
        # When value is None (GFK not resolved), try to read the
        # ``_prefetched_content_object`` attribute that the service layer
        # patches onto each BoardItem instance.
        if value is None:
            # Walk up to the serializer that holds the BoardItem instance.
            item_serializer = self.parent
            if item_serializer is not None:
                instance = item_serializer.instance
                if instance is not None:
                    value = getattr(instance, "_prefetched_content_object", None)
            if value is None:
                return None

        ct = ContentType.objects.get_for_model(value)
        key = f"{ct.app_label}.{ct.model}"
        prefix = _DETAIL_URL_MAP.get(key, f"/api/{ct.app_label}/{ct.model}/")
        detail_url = f"{prefix}{value.pk}/"
        # Normalise double slashes
        detail_url = detail_url.replace("//", "/")

        return {
            "content_type_id": ct.pk,
            "app_label": ct.app_label,
            "model": ct.model,
            "object_id": value.pk,
            "display_name": str(value),
            "detail_url": detail_url,
        }

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        """
        Validate and transform write payload into a content-type/object-id
        pair.

        Auto-resolve behaviour
        ----------------------
        When ``content_type_id`` is explicitly ``null`` (Python ``None``),
        the field automatically resolves the ``ContentType`` for
        ``evidence.Evidence``.  This lets the frontend omit the content type
        for the common case of pinning an Evidence object without having to
        look up the content-type pk first.

        A numeric value — whether correct or incorrect — bypasses
        auto-resolution and is validated as usual.
        """
        if not isinstance(data, dict):
            raise serializers.ValidationError(
                "Expected a dict with 'content_type_id' and 'object_id'."
            )

        raw_content_type_id = data.get("content_type_id")

        # Validate object_id independently so the error message is precise.
        try:
            object_id = int(data["object_id"])
        except (KeyError, TypeError, ValueError):
            raise serializers.ValidationError(
                "Both 'content_type_id' (int) and 'object_id' (int) are required."
            )

        # ── Auto-resolve when content_type_id is explicitly null ──────────
        if raw_content_type_id is None:
            try:
                ct = ContentType.objects.get(app_label="evidence", model="evidence")
            except ContentType.DoesNotExist:
                raise serializers.ValidationError(
                    "Evidence ContentType not found. Cannot auto-resolve content type."
                )
        else:
            # Numeric value provided – use normal lookup path.
            try:
                content_type_id = int(raw_content_type_id)
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    "Both 'content_type_id' (int) and 'object_id' (int) are required."
                )

            try:
                ct = ContentType.objects.get(pk=content_type_id)
            except ContentType.DoesNotExist:
                raise serializers.ValidationError(
                    f"ContentType with id {content_type_id} does not exist."
                )

        key = f"{ct.app_label}.{ct.model}"
        if key not in self.ALLOWED_CONTENT_TYPES:
            raise serializers.ValidationError(
                f"Content type '{key}' is not allowed on the detective board."
            )

        model_cls = ct.model_class()
        if model_cls is None or not model_cls.objects.filter(pk=object_id).exists():
            raise serializers.ValidationError(
                f"Object with id {object_id} does not exist for type '{key}'."
            )

        return {"content_type": ct, "object_id": object_id}


# ═══════════════════════════════════════════════════════════════════
#  DetectiveBoard Serializers
# ═══════════════════════════════════════════════════════════════════


class DetectiveBoardListSerializer(serializers.ModelSerializer):
    """
    Compact representation of a ``DetectiveBoard`` for list endpoints.

    Excludes nested items/connections/notes to keep the payload small.
    Includes ``item_count`` and ``connection_count`` as annotated fields
    so the frontend can show summary chips without a second request.
    """

    item_count = serializers.IntegerField(read_only=True)
    connection_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DetectiveBoard
        fields = [
            "id",
            "case",
            "detective",
            "item_count",
            "connection_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DetectiveBoardCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating or updating a ``DetectiveBoard``.

    ``detective`` defaults to ``request.user`` in the service layer and
    should NOT be accepted from the client (set ``read_only=True``).
    """

    class Meta:
        model = DetectiveBoard
        fields = ["id", "case", "detective"]
        read_only_fields = ["id", "detective"]

    def validate_case(self, value: Any) -> Any:
        """
        Ensure that no board already exists for the given case.
        """
        if DetectiveBoard.objects.filter(case=value).exists():
            raise serializers.ValidationError(
                "A detective board already exists for this case."
            )
        return value


class BoardNoteInlineSerializer(serializers.ModelSerializer):
    """Compact BoardNote used inside the full-board-state response."""

    class Meta:
        model = BoardNote
        fields = ["id", "title", "content", "created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class BoardItemInlineSerializer(serializers.ModelSerializer):
    """
    Compact ``BoardItem`` representation used inside the full-board-state
    response payload.

    ``content_object_summary`` is populated by ``GenericObjectRelatedField``
    so the frontend receives the resolved type/id/name for each pin.
    """

    content_object_summary = GenericObjectRelatedField(
        source="content_object",
        read_only=True,
    )

    class Meta:
        model = BoardItem
        fields = [
            "id",
            "content_type",
            "object_id",
            "content_object_summary",
            "position_x",
            "position_y",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BoardConnectionInlineSerializer(serializers.ModelSerializer):
    """Compact ``BoardConnection`` used inside the full-board-state response."""

    class Meta:
        model = BoardConnection
        fields = ["id", "from_item", "to_item", "label", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class FullBoardStateSerializer(serializers.ModelSerializer):
    """
    **The most important read serializer in the board app.**

    Returns a single ``DetectiveBoard`` together with *all* nested
    relationships (items, connections, notes) in one payload.

    This prevents an N+1 waterfall of API calls from the Next.js canvas
    renderer.  The service layer (``BoardWorkspaceService.get_full_board_graph``)
    MUST use ``select_related`` and ``prefetch_related`` so that this
    serializer never triggers additional database queries beyond the initial
    prefetched sets.

    Response shape::

        {
          "id": 1,
          "case": 5,
          "detective": 3,
          "items": [ { ...BoardItemInlineSerializer... }, ... ],
          "connections": [ { ...BoardConnectionInlineSerializer... }, ... ],
          "notes": [ { ...BoardNoteInlineSerializer... }, ... ],
          "created_at": "...",
          "updated_at": "..."
        }
    """

    items = BoardItemInlineSerializer(many=True, read_only=True)
    connections = BoardConnectionInlineSerializer(many=True, read_only=True)
    notes = BoardNoteInlineSerializer(many=True, read_only=True)

    class Meta:
        model = DetectiveBoard
        fields = [
            "id",
            "case",
            "detective",
            "items",
            "connections",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "detective", "created_at", "updated_at"]


# ═══════════════════════════════════════════════════════════════════
#  BoardItem Serializers
# ═══════════════════════════════════════════════════════════════════


class BoardItemCreateSerializer(serializers.Serializer):
    """
    Validates the request body for adding a new item to a board.

    Accepts a ``content_object`` payload (``content_type_id`` + ``object_id``)
    via ``GenericObjectRelatedField`` and optional initial coordinates.
    The ``board`` is resolved from the URL kwarg in the view and injected
    by the service, not from the request body.

    Request body example::

        {
          "content_object": { "content_type_id": 7, "object_id": 42 },
          "position_x": 120.5,
          "position_y": 300.0
        }
    """

    content_object = GenericObjectRelatedField()
    position_x = serializers.FloatField(default=0.0)
    position_y = serializers.FloatField(default=0.0)


class BoardItemUpdatePositionSerializer(serializers.Serializer):
    """
    Single item payload used inside ``BatchCoordinateUpdateSerializer``.

    Validates that each element of the batch array has an integer ``id``
    and valid float coordinates.
    """

    id = serializers.IntegerField(
        help_text="Primary key of the ``BoardItem`` to reposition.",
    )
    position_x = serializers.FloatField()
    position_y = serializers.FloatField()


class BatchCoordinateUpdateSerializer(serializers.Serializer):
    """
    Validates the batch drag-and-drop coordinate save request.

    Accepts a list of ``{id, position_x, position_y}`` objects and
    validates each one before passing the cleaned list to
    ``BoardItemService.update_batch_coordinates``.

    Performance contract
    --------------------
    The service layer MUST execute this with a single
    ``bulk_update(fields=["position_x", "position_y"])`` call, *not*
    a loop of individual ``save()`` calls, to minimise database round
    trips when the user drops 30+ items during a canvas rearrangement.

    Request body example::

        {
          "items": [
            {"id": 1, "position_x": 100.0, "position_y": 200.0},
            {"id": 2, "position_x": 350.5, "position_y": 80.0}
          ]
        }
    """

    items = BoardItemUpdatePositionSerializer(many=True, allow_empty=False)

    def validate_items(self, value: list[dict]) -> list[dict]:
        """
        Ensure item IDs are unique within the batch.
        """
        ids = [item["id"] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Duplicate item IDs in batch.")
        return value


class BoardItemResponseSerializer(serializers.ModelSerializer):
    """Full read representation of a single ``BoardItem`` after creation."""

    content_object_summary = GenericObjectRelatedField(
        source="content_object",
        read_only=True,
    )

    class Meta:
        model = BoardItem
        fields = [
            "id",
            "board",
            "content_type",
            "object_id",
            "content_object_summary",
            "position_x",
            "position_y",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "board", "created_at", "updated_at"]


# ═══════════════════════════════════════════════════════════════════
#  BoardConnection Serializers
# ═══════════════════════════════════════════════════════════════════


class BoardConnectionCreateSerializer(serializers.ModelSerializer):
    """
    Validates the request body for creating a red-line connection.

    Both ``from_item`` and ``to_item`` must belong to the same board
    (validated in the service layer, not here).

    Cross-field validation stub: the serializer validates that
    ``from_item != to_item`` (no self-loops).
    """

    class Meta:
        model = BoardConnection
        fields = ["id", "from_item", "to_item", "label"]
        read_only_fields = ["id"]

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Prevent self-loop connections (from_item == to_item).
        """
        if attrs["from_item"] == attrs["to_item"]:
            raise serializers.ValidationError(
                "A BoardItem cannot be connected to itself."
            )
        return attrs


class BoardConnectionResponseSerializer(serializers.ModelSerializer):
    """Full read representation of a ``BoardConnection``."""

    class Meta:
        model = BoardConnection
        fields = ["id", "board", "from_item", "to_item", "label", "created_at", "updated_at"]
        read_only_fields = ["id", "board", "created_at", "updated_at"]


# ═══════════════════════════════════════════════════════════════════
#  BoardNote Serializers
# ═══════════════════════════════════════════════════════════════════


class BoardNoteCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Validates input for creating or updating a sticky note on the board.

    ``board`` is resolved from the URL kwarg and injected by the service.
    ``created_by`` defaults to ``request.user`` in the service — not
    accepted from the client.
    """

    class Meta:
        model = BoardNote
        fields = ["id", "title", "content", "created_by"]
        read_only_fields = ["id", "created_by"]


class BoardNoteResponseSerializer(serializers.ModelSerializer):
    """Full read representation of a ``BoardNote``."""

    class Meta:
        model = BoardNote
        fields = [
            "id",
            "board",
            "title",
            "content",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "board", "created_by", "created_at", "updated_at"]
