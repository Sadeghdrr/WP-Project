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
#  Generic Object Field
# ═══════════════════════════════════════════════════════════════════


class GenericObjectRelatedField(serializers.Field):
    """
    Custom DRF field to serialize/deserialize Django ``GenericForeignKey``
    fields on ``BoardItem``.

    Read Behaviour (serialisation)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Inspects the resolved ``content_object`` and returns a lightweight
    dictionary::

        {
            "content_type_id": 7,
            "app_label":       "evidence",
            "model":           "biologicalevidence",
            "object_id":       42,
            "display_name":    "Hair Sample #42",
            "detail_url":      "/api/evidence/biological/42/"
        }

    The ``display_name`` is derived by calling ``str()`` on the object.
    The ``detail_url`` is constructed from a registry of known app routers
    so that the frontend can deep-link without knowing the URL structure.

    Write Behaviour (deserialisation)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Expects a dict with exactly two keys::

        { "content_type_id": <int>, "object_id": <int> }

    Validation steps:
    1. Assert ``content_type_id`` resolves to a real ``ContentType`` record.
    2. Assert the model class identified by that ``ContentType`` is in the
       ``ALLOWED_CONTENT_TYPES`` allowlist (prevent linking arbitrary models).
    3. Query ``Model.objects.filter(pk=object_id).exists()`` to confirm the
       target object exists.
    4. Return a tuple ``(content_type, object_id)`` for the service layer to
       consume.
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

    def to_representation(self, value: Any) -> dict[str, Any]:
        """
        Convert a resolved ``content_object`` into a JSON-serialisable dict.

        Parameters
        ----------
        value : Any
            The Python object stored on ``BoardItem.content_object``.

        Returns
        -------
        dict
            A compact summary dict. Returns ``None`` if the linked object
            has been deleted (orphan protection).

        Implementation Contract
        -----------------------
        1. Return ``None`` (or raise ``ValidationError``) if ``value`` is
           ``None`` (deleted referenced object).
        2. Retrieve the ``ContentType`` for ``value`` via
           ``ContentType.objects.get_for_model(value)``.
        3. Build the ``detail_url`` from a hardcoded mapping
           ``{app_label}.{model_name}`` → URL prefix.
        4. Return the dict described in the class docstring.
        """
        raise NotImplementedError

    def to_internal_value(self, data: Any) -> dict[str, Any]:
        """
        Validate and transform write payload into a content-type/object-id
        pair.

        Parameters
        ----------
        data : Any
            Raw value from the incoming request body.  Must be a dict with
            ``content_type_id`` (int) and ``object_id`` (int).

        Returns
        -------
        dict
            ``{"content_type": <ContentType>, "object_id": <int>}`` —
            ready for the service layer.

        Raises
        ------
        serializers.ValidationError
            If the content type is unknown, not in the allowlist, or the
            target object does not exist.

        Implementation Contract
        -----------------------
        1. Validate ``data`` is a dict; raise ``ValidationError`` otherwise.
        2. Extract and coerce ``content_type_id`` and ``object_id``.
        3. ``ContentType.objects.get(pk=content_type_id)`` — raise 400 if
           DoesNotExist.
        4. Build the ``"app_label.model"`` key and check against
           ``ALLOWED_CONTENT_TYPES``.
        5. ``ct.model_class().objects.filter(pk=object_id).exists()`` — raise
           400 if False.
        6. Return ``{"content_type": ct, "object_id": object_id}``.
        """
        raise NotImplementedError


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

        Implementation Contract
        -----------------------
        Delegate uniqueness check to the service layer; raise
        ``serializers.ValidationError`` with a human-readable message if a
        board already exists (``DetectiveBoard.objects.filter(case=value).exists()``).
        """
        raise NotImplementedError


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

        Implementation Contract
        -----------------------
        Extract the list of ``id`` values; if ``len(ids) != len(set(ids))``
        raise ``ValidationError("Duplicate item IDs in batch.")``.
        """
        raise NotImplementedError


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

        Implementation Contract
        -----------------------
        If ``attrs["from_item"] == attrs["to_item"]`` raise
        ``ValidationError("A BoardItem cannot be connected to itself.")``.
        Further cross-board ownership validation MUST be done in the service
        layer (where access to ``board_id`` from the URL context is available).
        """
        raise NotImplementedError


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
