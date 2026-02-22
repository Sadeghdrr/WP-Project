"""
Board app ViewSets.

Architecture: Views are intentionally thin.
Every view follows a strict three-step pattern:

    1. Parse and validate input via a serializer.
    2. Delegate all business logic to the appropriate service class.
    3. Serialize the result and return a DRF ``Response``.

No database queries, permission guards, or domain logic live here —
those belong exclusively in ``services.py``.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)

from .models import BoardConnection, BoardItem, BoardNote, DetectiveBoard
from .serializers import (
    BatchCoordinateUpdateSerializer,
    BoardConnectionCreateSerializer,
    BoardConnectionResponseSerializer,
    BoardItemCreateSerializer,
    BoardItemResponseSerializer,
    BoardNoteCreateUpdateSerializer,
    BoardNoteResponseSerializer,
    DetectiveBoardCreateUpdateSerializer,
    DetectiveBoardListSerializer,
    FullBoardStateSerializer,
)
from .services import (
    BoardConnectionService,
    BoardItemService,
    BoardNoteService,
    BoardWorkspaceService,
)


# ═══════════════════════════════════════════════════════════════════
#  DetectiveBoard ViewSet
# ═══════════════════════════════════════════════════════════════════


class DetectiveBoardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ``DetectiveBoard`` CRUD and the full-graph read endpoint.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BoardWorkspaceService.list_boards(self.request.user)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return DetectiveBoardListSerializer
        if self.action == "full_state":
            return FullBoardStateSerializer
        return DetectiveBoardCreateUpdateSerializer

    @extend_schema(
        summary="Create a detective board",
        description="Create a new detective board for an existing case.",
        request=DetectiveBoardCreateUpdateSerializer,
        responses={
            201: OpenApiResponse(response=DetectiveBoardListSerializer, description="Board created."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Detective Board"],
    )
    def create(self, request: Request, *args, **kwargs) -> Response:
        serializer = DetectiveBoardCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        board = BoardWorkspaceService.create_board(
            serializer.validated_data, request.user
        )
        return Response(
            DetectiveBoardListSerializer(board).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Partial update board metadata",
        description="Update title or other metadata fields of a detective board.",
        request=DetectiveBoardCreateUpdateSerializer,
        responses={
            200: OpenApiResponse(response=DetectiveBoardListSerializer, description="Board updated."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Detective Board"],
    )
    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        board = self.get_object()
        serializer = DetectiveBoardCreateUpdateSerializer(
            data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        board = BoardWorkspaceService.update_board(
            board, serializer.validated_data, request.user
        )
        return Response(DetectiveBoardListSerializer(board).data)

    @extend_schema(
        summary="Delete a detective board",
        description="Delete a detective board and all its nested items.",
        responses={204: OpenApiResponse(description="Deleted.")},
        tags=["Detective Board"],
    )
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        board = self.get_object()
        BoardWorkspaceService.delete_board(board, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="full")
    @extend_schema(
        summary="Full board graph (single request)",
        description=(
            "Return the complete board graph — metadata, items (with resolved "
            "GenericForeignKey summaries), connections, and notes — in a single response. "
            "Designed for the Next.js canvas to call on mount."
        ),
        responses={200: OpenApiResponse(response=FullBoardStateSerializer, description="Full board state.")},
        tags=["Detective Board"],
    )
    def full_state(self, request: Request, pk: int = None) -> Response:
        board = BoardWorkspaceService.get_board_snapshot(int(pk), request.user)
        serializer = FullBoardStateSerializer(board, context={"request": request})
        return Response(serializer.data)


# ═══════════════════════════════════════════════════════════════════
#  BoardItem ViewSet
# ═══════════════════════════════════════════════════════════════════


class BoardItemViewSet(viewsets.ViewSet):
    """
    ViewSet for managing pins (``BoardItem``s) on a detective board.
    """

    permission_classes = [IsAuthenticated]

    def _get_board(self, board_pk: int) -> DetectiveBoard:
        return get_object_or_404(DetectiveBoard, pk=board_pk)

    @extend_schema(
        summary="Add a pin to the board",
        description="Pin a content object (evidence, suspect, etc.) onto the detective board.",
        request=BoardItemCreateSerializer,
        responses={
            201: OpenApiResponse(response=BoardItemResponseSerializer, description="Pin created."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Detective Board – Items"],
    )
    def create(self, request: Request, board_pk: int = None) -> Response:
        board = self._get_board(board_pk)
        serializer = BoardItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        co = serializer.validated_data["content_object"]
        item = BoardItemService.add_item(
            board=board,
            content_type=co["content_type"],
            object_id=co["object_id"],
            position_x=serializer.validated_data.get("position_x", 0.0),
            position_y=serializer.validated_data.get("position_y", 0.0),
            requesting_user=request.user,
        )
        return Response(
            BoardItemResponseSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Remove a pin from the board",
        description="Remove a board item (pin) by ID.",
        responses={204: OpenApiResponse(description="Pin removed.")},
        tags=["Detective Board – Items"],
    )
    def destroy(self, request: Request, board_pk: int = None, pk: int = None) -> Response:
        item = get_object_or_404(BoardItem, pk=pk, board__pk=board_pk)
        BoardItemService.remove_item(item, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["patch"],
        url_path="batch-coordinates",
    )
    @extend_schema(
        summary="Batch update pin coordinates",
        description=(
            "Drag-and-drop save endpoint. Accepts an array of item ID + new position pairs "
            "and performs a single bulk update."
        ),
        request=BatchCoordinateUpdateSerializer,
        responses={
            200: OpenApiResponse(response=BoardItemResponseSerializer(many=True), description="Updated positions."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Detective Board – Items"],
    )
    def batch_update_coordinates(
        self, request: Request, board_pk: int = None
    ) -> Response:
        board = self._get_board(board_pk)
        serializer = BatchCoordinateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_items = BoardItemService.update_batch_coordinates(
            board,
            serializer.validated_data["items"],
            request.user,
        )
        return Response(
            BoardItemResponseSerializer(updated_items, many=True).data,
            status=status.HTTP_200_OK,
        )


# ═══════════════════════════════════════════════════════════════════
#  BoardConnection ViewSet
# ═══════════════════════════════════════════════════════════════════


class BoardConnectionViewSet(viewsets.ViewSet):
    """
    ViewSet for managing red-line connections (``BoardConnection``s).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Create a board connection",
        description="Draw a red-line connection between two board items.",
        request=BoardConnectionCreateSerializer,
        responses={
            201: OpenApiResponse(response=BoardConnectionResponseSerializer, description="Connection created."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Detective Board – Connections"],
    )
    def create(self, request: Request, board_pk: int = None) -> Response:
        board = get_object_or_404(DetectiveBoard, pk=board_pk)
        serializer = BoardConnectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        connection = BoardConnectionService.create_connection(
            board=board,
            from_item=serializer.validated_data["from_item"],
            to_item=serializer.validated_data["to_item"],
            label=serializer.validated_data.get("label", ""),
            requesting_user=request.user,
        )
        return Response(
            BoardConnectionResponseSerializer(connection).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Delete a board connection",
        description="Remove a red-line connection from the board.",
        responses={204: OpenApiResponse(description="Connection removed.")},
        tags=["Detective Board – Connections"],
    )
    def destroy(
        self, request: Request, board_pk: int = None, pk: int = None
    ) -> Response:
        connection = get_object_or_404(
            BoardConnection, pk=pk, board__pk=board_pk
        )
        BoardConnectionService.delete_connection(connection, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ═══════════════════════════════════════════════════════════════════
#  BoardNote ViewSet
# ═══════════════════════════════════════════════════════════════════


class BoardNoteViewSet(viewsets.ViewSet):
    """
    ViewSet for sticky-note (``BoardNote``) CRUD.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Create a sticky note",
        description="Add a new sticky note to the detective board.",
        request=BoardNoteCreateUpdateSerializer,
        responses={
            201: OpenApiResponse(response=BoardNoteResponseSerializer, description="Note created."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Detective Board – Notes"],
    )
    def create(self, request: Request, board_pk: int = None) -> Response:
        board = get_object_or_404(DetectiveBoard, pk=board_pk)
        serializer = BoardNoteCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = BoardNoteService.create_note(
            board, serializer.validated_data, request.user
        )
        return Response(
            BoardNoteResponseSerializer(note).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Retrieve a sticky note",
        description="Fetch a single board note by ID.",
        responses={200: OpenApiResponse(response=BoardNoteResponseSerializer, description="Note detail.")},
        tags=["Detective Board – Notes"],
    )
    def retrieve(
        self, request: Request, board_pk: int = None, pk: int = None
    ) -> Response:
        note = get_object_or_404(BoardNote, pk=pk, board__pk=board_pk)
        return Response(BoardNoteResponseSerializer(note).data)

    @extend_schema(
        summary="Update a sticky note",
        description="Partially update a sticky note’s title and/or content.",
        request=BoardNoteCreateUpdateSerializer,
        responses={
            200: OpenApiResponse(response=BoardNoteResponseSerializer, description="Note updated."),
            400: OpenApiResponse(description="Validation error."),
        },
        tags=["Detective Board – Notes"],
    )
    def partial_update(
        self, request: Request, board_pk: int = None, pk: int = None
    ) -> Response:
        note = get_object_or_404(BoardNote, pk=pk, board__pk=board_pk)
        serializer = BoardNoteCreateUpdateSerializer(
            data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        note = BoardNoteService.update_note(
            note, serializer.validated_data, request.user
        )
        return Response(BoardNoteResponseSerializer(note).data)

    @extend_schema(
        summary="Delete a sticky note",
        description="Remove a sticky note from the detective board.",
        responses={204: OpenApiResponse(description="Note deleted.")},
        tags=["Detective Board – Notes"],
    )
    def destroy(
        self, request: Request, board_pk: int = None, pk: int = None
    ) -> Response:
        note = get_object_or_404(BoardNote, pk=pk, board__pk=board_pk)
        BoardNoteService.delete_note(note, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)
