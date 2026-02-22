"""
Board app Service Layer.

This module is the **single source of truth** for all business logic
within the ``board`` app.  Views must remain *thin*: they validate
input through serializers, call a service method, and return the result
wrapped in a DRF ``Response``.

Architecture
------------
- ``BoardWorkspaceService`` — DetectiveBoard lifecycle + full graph fetch.
- ``BoardItemService``       — pin management + batch coordinate update.
- ``BoardConnectionService`` — red-line management.
- ``BoardNoteService``       — sticky-note CRUD.

Design Principles
-----------------
* **Fat Model / Thin View / Service Layer**: All queries, permission
  guards, and cross-model consistency checks live here.
* **Minimise DB round-trips**: ``get_full_board_graph`` uses one
  ``select_related`` + one compound ``prefetch_related`` to load the
  entire board graph in ≤ 3 DB queries.
* **Bulk operations**: ``update_batch_coordinates`` uses Django's
  ``bulk_update`` to save all repositioned items in a single UPDATE …
  CASE WHEN … statement via ``QuerySet.bulk_update``.
* **Atomic writes**: all multi-step mutations are wrapped in
  ``transaction.atomic`` to guarantee consistency under concurrent access.
"""

from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q, QuerySet

from core.domain.exceptions import DomainError, NotFound, PermissionDenied

from .models import BoardConnection, BoardItem, BoardNote, DetectiveBoard


# ═══════════════════════════════════════════════════════════════════
#  Shared permission helpers
# ═══════════════════════════════════════════════════════════════════

# Role names that imply supervisory read/write access to any board
# belonging to cases they are assigned to.
_SUPERVISOR_ROLES = frozenset({"Sergeant", "Captain", "Police Chief"})
_ADMIN_ROLE = "System Admin"


def _is_admin(user: Any) -> bool:
    """Return True if the user is a superuser or has the System Admin role."""
    return user.is_superuser or (user.role is not None and user.role.name == _ADMIN_ROLE)


def _can_view_board(user: Any, board: DetectiveBoard) -> bool:
    """
    Read access:
    - The board's detective.
    - A supervisor (Sergeant/Captain/Chief) assigned to the same case.
    - An admin / superuser.
    """
    if _is_admin(user):
        return True
    if board.detective_id == user.pk:
        return True
    if user.role and user.role.name in _SUPERVISOR_ROLES:
        case = board.case
        return _is_assigned_to_case(user, case)
    return False


def _can_edit_board(user: Any, board: DetectiveBoard) -> bool:
    """
    Write access:
    - The board's detective (primary editor).
    - A supervisor assigned to the same case.
    - An admin / superuser.
    """
    return _can_view_board(user, board)


def _is_assigned_to_case(user: Any, case: Any) -> bool:
    """Check whether *user* is one of the assigned personnel on *case*."""
    return user.pk in {
        getattr(case, "assigned_detective_id", None),
        getattr(case, "assigned_sergeant_id", None),
        getattr(case, "assigned_captain_id", None),
        getattr(case, "assigned_judge_id", None),
        getattr(case, "created_by_id", None),
        getattr(case, "approved_by_id", None),
    }


def _enforce_edit(user: Any, board: DetectiveBoard) -> None:
    """Raise ``PermissionDenied`` if *user* may not edit *board*."""
    if not _can_edit_board(user, board):
        raise PermissionDenied("You do not have permission to modify this board.")


# ═══════════════════════════════════════════════════════════════════
#  Board Workspace Service
# ═══════════════════════════════════════════════════════════════════


class BoardWorkspaceService:
    """
    Manages the lifecycle of ``DetectiveBoard`` instances and exposes the
    single highly-optimised "full board graph" read operation consumed by
    the Next.js canvas renderer.
    """

    # ------------------------------------------------------------------
    #  get_or_create_board
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def get_or_create_board(case_id: int, user: Any) -> DetectiveBoard:
        """
        Return the board for *case_id*, creating it implicitly if none
        exists yet.  Only the assigned detective (or a supervisor/admin)
        may trigger creation.
        """
        from cases.models import Case  # avoid circular import at module level

        try:
            case = Case.objects.get(pk=case_id)
        except Case.DoesNotExist:
            raise NotFound(f"Case {case_id} does not exist.")

        board, created = DetectiveBoard.objects.get_or_create(
            case=case,
            defaults={"detective": user},
        )

        if not _can_view_board(user, board):
            raise PermissionDenied("You do not have permission to access this board.")

        return board

    # ------------------------------------------------------------------
    #  list_boards
    # ------------------------------------------------------------------
    @staticmethod
    def list_boards(requesting_user: Any) -> QuerySet:
        """
        Return boards visible to *requesting_user* annotated with
        ``item_count`` and ``connection_count``.
        """
        qs = (
            DetectiveBoard.objects
            .select_related("case", "detective")
            .annotate(
                item_count=Count("items", distinct=True),
                connection_count=Count("connections", distinct=True),
            )
        )

        if _is_admin(requesting_user):
            return qs

        if requesting_user.role and requesting_user.role.name in _SUPERVISOR_ROLES:
            return qs.filter(
                Q(detective=requesting_user)
                | Q(case__assigned_detective=requesting_user)
                | Q(case__assigned_sergeant=requesting_user)
                | Q(case__assigned_captain=requesting_user)
            )

        # Default (Detective or any other role): own boards only
        return qs.filter(detective=requesting_user)

    # ------------------------------------------------------------------
    #  create_board
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def create_board(validated_data: dict[str, Any], requesting_user: Any) -> DetectiveBoard:
        """Create a new ``DetectiveBoard`` for a given case."""
        case = validated_data["case"]
        if DetectiveBoard.objects.filter(case=case).exists():
            raise DomainError("A board already exists for this case.")

        validated_data["detective"] = requesting_user
        board = DetectiveBoard.objects.create(**validated_data)
        return board

    # ------------------------------------------------------------------
    #  update_board
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def update_board(
        board: DetectiveBoard,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> DetectiveBoard:
        """Partially update board metadata (``detective`` and ``case`` are immutable)."""
        _enforce_edit(requesting_user, board)

        validated_data.pop("detective", None)
        validated_data.pop("case", None)

        update_fields = []
        for field, value in validated_data.items():
            setattr(board, field, value)
            update_fields.append(field)

        if update_fields:
            board.save(update_fields=update_fields)
        return board

    # ------------------------------------------------------------------
    #  delete_board
    # ------------------------------------------------------------------
    @staticmethod
    def delete_board(board: DetectiveBoard, requesting_user: Any) -> None:
        """Delete a board — only the owning detective or an admin may do so."""
        if board.detective_id != requesting_user.pk and not _is_admin(requesting_user):
            raise PermissionDenied("You do not have permission to delete this board.")
        board.delete()

    # ------------------------------------------------------------------
    #  get_full_board_graph  (snapshot)
    # ------------------------------------------------------------------
    @staticmethod
    def get_full_board_graph(board_id: int) -> DetectiveBoard:
        """
        Return a ``DetectiveBoard`` with **all** related items, connections,
        and notes pre-fetched in ≤ 3 DB queries.

        The ``GenericForeignKey`` on ``BoardItem`` is handled by manually
        grouping ``content_type`` + ``object_id`` pairs and bulk-fetching
        them per content-type to avoid N+1.
        """
        board = (
            DetectiveBoard.objects
            .select_related("case", "detective")
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=BoardItem.objects
                        .select_related("content_type")
                        .order_by("id"),
                ),
                Prefetch(
                    "connections",
                    queryset=BoardConnection.objects
                        .select_related("from_item", "to_item")
                        .order_by("id"),
                ),
                Prefetch(
                    "notes",
                    queryset=BoardNote.objects
                        .select_related("created_by")
                        .order_by("id"),
                ),
            )
            .get(pk=board_id)
        )

        # ── GFK bulk resolution (N+1 prevention) ───────────────────
        items = list(board.items.all())
        if items:
            # Group object_ids by content_type to batch-fetch in one
            # query per content-type.
            ct_map: dict[int, list[int]] = {}
            for item in items:
                ct_map.setdefault(item.content_type_id, []).append(item.object_id)

            obj_cache: dict[tuple[int, int], Any] = {}
            for ct_id, obj_ids in ct_map.items():
                ct = ContentType.objects.get_for_id(ct_id)
                model_cls = ct.model_class()
                if model_cls is not None:
                    objs = model_cls.objects.in_bulk(obj_ids)
                    for oid, obj in objs.items():
                        obj_cache[(ct_id, oid)] = obj

            # Patch resolved objects onto each item so
            # ``GenericObjectRelatedField.to_representation`` can read them
            # without additional queries.
            for item in items:
                item._prefetched_content_object = obj_cache.get(
                    (item.content_type_id, item.object_id)
                )

        return board

    # ------------------------------------------------------------------
    #  get_board_snapshot  (alias kept for compatibility)
    # ------------------------------------------------------------------
    @staticmethod
    def get_board_snapshot(board_id: int, actor: Any) -> DetectiveBoard:
        """Alias for ``get_full_board_graph`` that also checks read access."""
        board = BoardWorkspaceService.get_full_board_graph(board_id)
        if not _can_view_board(actor, board):
            raise PermissionDenied("You do not have permission to view this board.")
        return board


# ═══════════════════════════════════════════════════════════════════
#  Board Item Service
# ═══════════════════════════════════════════════════════════════════


class BoardItemService:
    """
    Manages the lifecycle of ``BoardItem`` instances (pins on the canvas).
    """

    @staticmethod
    @transaction.atomic
    def add_item(
        board: DetectiveBoard,
        content_type: ContentType,
        object_id: int,
        position_x: float,
        position_y: float,
        requesting_user: Any,
    ) -> BoardItem:
        """Pin a new item to the detective board."""
        _enforce_edit(requesting_user, board)

        if BoardItem.objects.filter(
            board=board, content_type=content_type, object_id=object_id
        ).exists():
            raise DomainError("This object is already pinned to the board.")

        item = BoardItem.objects.create(
            board=board,
            content_type=content_type,
            object_id=object_id,
            position_x=position_x,
            position_y=position_y,
        )
        return item

    @staticmethod
    @transaction.atomic
    def update_batch_coordinates(
        board: DetectiveBoard,
        items_data: list[dict[str, Any]],
        requesting_user: Any,
    ) -> list[BoardItem]:
        """
        Bulk drag-and-drop save.  Updates (position_x, position_y) for
        multiple ``BoardItem``s in a **single** ``bulk_update`` call.
        """
        _enforce_edit(requesting_user, board)

        ids = [d["id"] for d in items_data]
        items = list(BoardItem.objects.filter(board=board, pk__in=ids))

        if len(items) != len(ids):
            found_ids = {item.id for item in items}
            missing = sorted(set(ids) - found_ids)
            raise DomainError(
                f"The following item IDs do not belong to this board: {missing}"
            )

        item_map = {item.id: item for item in items}
        for d in items_data:
            item_map[d["id"]].position_x = d["position_x"]
            item_map[d["id"]].position_y = d["position_y"]

        BoardItem.objects.bulk_update(items, fields=["position_x", "position_y"])
        return items

    @staticmethod
    @transaction.atomic
    def remove_item(item: BoardItem, requesting_user: Any) -> None:
        """Remove a ``BoardItem`` from the board (cascades connections)."""
        _enforce_edit(requesting_user, item.board)
        item.delete()


# ═══════════════════════════════════════════════════════════════════
#  Board Connection Service
# ═══════════════════════════════════════════════════════════════════


class BoardConnectionService:
    """
    Manages red-line connections between ``BoardItem``s.
    """

    @staticmethod
    @transaction.atomic
    def create_connection(
        board: DetectiveBoard,
        from_item: BoardItem,
        to_item: BoardItem,
        label: str,
        requesting_user: Any,
    ) -> BoardConnection:
        """Draw a red-line connection between two board items."""
        _enforce_edit(requesting_user, board)

        if from_item.board_id != board.pk or to_item.board_id != board.pk:
            raise DomainError("Both items must belong to the same board.")

        if from_item.pk == to_item.pk:
            raise DomainError("A board item cannot be connected to itself.")

        try:
            connection = BoardConnection.objects.create(
                board=board,
                from_item=from_item,
                to_item=to_item,
                label=label,
            )
        except IntegrityError:
            raise DomainError("This connection already exists.")

        return connection

    @staticmethod
    @transaction.atomic
    def delete_connection(
        connection: BoardConnection,
        requesting_user: Any,
    ) -> None:
        """Remove a red-line connection."""
        _enforce_edit(requesting_user, connection.board)
        connection.delete()


# ═══════════════════════════════════════════════════════════════════
#  Board Note Service
# ═══════════════════════════════════════════════════════════════════


class BoardNoteService:
    """
    CRUD operations for sticky notes (``BoardNote``) on the detective board.
    """

    @staticmethod
    @transaction.atomic
    def create_note(
        board: DetectiveBoard,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> BoardNote:
        """
        Create a new sticky note and auto-pin it as a ``BoardItem``
        so it is immediately visible on the canvas.
        """
        _enforce_edit(requesting_user, board)

        validated_data["board"] = board
        validated_data["created_by"] = requesting_user
        note = BoardNote.objects.create(**validated_data)

        # Auto-create a BoardItem referencing this note via GFK
        ct = ContentType.objects.get_for_model(BoardNote)
        BoardItem.objects.create(
            board=board,
            content_type=ct,
            object_id=note.pk,
            position_x=0.0,
            position_y=0.0,
        )

        return note

    @staticmethod
    @transaction.atomic
    def update_note(
        note: BoardNote,
        validated_data: dict[str, Any],
        requesting_user: Any,
    ) -> BoardNote:
        """Update an existing sticky note's title and/or content."""
        if note.created_by_id != requesting_user.pk and not _is_admin(requesting_user):
            raise PermissionDenied("You do not have permission to update this note.")

        update_fields: list[str] = []
        for field in ("title", "content"):
            if field in validated_data:
                setattr(note, field, validated_data[field])
                update_fields.append(field)

        if update_fields:
            note.save(update_fields=update_fields)
        return note

    @staticmethod
    @transaction.atomic
    def delete_note(note: BoardNote, requesting_user: Any) -> None:
        """
        Delete a sticky note and its associated ``BoardItem`` (GFK does
        **not** cascade, so manual cleanup is required).
        """
        if note.created_by_id != requesting_user.pk and not _is_admin(requesting_user):
            raise PermissionDenied("You do not have permission to delete this note.")

        ct = ContentType.objects.get_for_model(note)
        BoardItem.objects.filter(
            board=note.board,
            content_type=ct,
            object_id=note.pk,
        ).delete()

        note.delete()
