"""
Board app models.

Implements the **Detective Board** — a visual workspace where a Detective
places evidence items, notes, and documents at arbitrary X/Y coordinates
and draws "red lines" (connections) between related items.

Uses Django's ``GenericForeignKey`` on ``BoardItem`` so that *any* model
(currently ``Evidence`` or ``BoardNote``) can be pinned to the board.
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from core.models import TimeStampedModel
from core.permissions_constants import BoardPerms


class DetectiveBoard(TimeStampedModel):
    """
    One detective board per case.  Owned by the assigned detective.

    The frontend renders items at their (x, y) positions and draws lines
    for each ``BoardConnection``.  The board can optionally be exported as
    an image and attached to the detective's report.
    """

    case = models.OneToOneField(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="detective_board",
        verbose_name="Case",
    )
    detective = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="detective_boards",
        verbose_name="Detective",
    )

    class Meta:
        verbose_name = "Detective Board"
        verbose_name_plural = "Detective Boards"
        permissions = [
            (BoardPerms.CAN_EXPORT_BOARD, "Can export detective board as image"),
            (BoardPerms.CAN_CREATE_BOARD, "Can create a detective board"),
            (BoardPerms.CAN_VIEW_ANY_BOARD, "Supervisor: view boards on assigned cases"),
        ]

    def __str__(self):
        return f"Board for Case #{self.case_id}"


class BoardNote(TimeStampedModel):
    """
    Free-form note that can be pinned to a ``DetectiveBoard``.

    Notes complement evidence items — they hold the detective's reasoning,
    hypotheses, or annotations.
    """

    board = models.ForeignKey(
        DetectiveBoard,
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name="Board",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
    )
    content = models.TextField(
        blank=True,
        default="",
        verbose_name="Content",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="board_notes",
        verbose_name="Created By",
    )

    class Meta:
        verbose_name = "Board Note"
        verbose_name_plural = "Board Notes"

    def __str__(self):
        return self.title


class BoardItem(TimeStampedModel):
    """
    A single draggable element on the detective board.

    Uses a ``GenericForeignKey`` so the item can reference **any** model —
    currently ``Evidence`` (and its sub-types) or ``BoardNote``.

    ``position_x`` / ``position_y`` store the pixel or percentage
    coordinates on the board canvas (frontend decides the unit).
    """

    board = models.ForeignKey(
        DetectiveBoard,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Board",
    )

    # ── Generic link to the underlying object ───────────────────────
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="Content Type",
    )
    object_id = models.PositiveIntegerField(
        verbose_name="Object ID",
    )
    content_object = GenericForeignKey("content_type", "object_id")

    # ── Position on the board canvas ────────────────────────────────
    position_x = models.FloatField(
        default=0.0,
        verbose_name="X Coordinate",
    )
    position_y = models.FloatField(
        default=0.0,
        verbose_name="Y Coordinate",
    )

    class Meta:
        verbose_name = "Board Item"
        verbose_name_plural = "Board Items"
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return (
            f"Item on Board #{self.board_id} "
            f"at ({self.position_x}, {self.position_y})"
        )


class BoardConnection(TimeStampedModel):
    """
    A "red line" connecting two ``BoardItem``s on the detective board.

    Represents a logical link the detective draws between two pieces of
    evidence or notes.  Both endpoints must belong to the same board.
    """

    board = models.ForeignKey(
        DetectiveBoard,
        on_delete=models.CASCADE,
        related_name="connections",
        verbose_name="Board",
    )
    from_item = models.ForeignKey(
        BoardItem,
        on_delete=models.CASCADE,
        related_name="connections_from",
        verbose_name="From Item",
    )
    to_item = models.ForeignKey(
        BoardItem,
        on_delete=models.CASCADE,
        related_name="connections_to",
        verbose_name="To Item",
    )
    label = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Connection Label",
        help_text="Optional annotation on the red line.",
    )

    class Meta:
        verbose_name = "Board Connection"
        verbose_name_plural = "Board Connections"
        unique_together = [("from_item", "to_item")]

    def __str__(self):
        return (
            f"Connection: Item #{self.from_item_id} "
            f"↔ Item #{self.to_item_id}"
        )
