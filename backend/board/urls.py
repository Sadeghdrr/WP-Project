"""
Board app URL configuration.

Registers all Detective Board routes using DRF routers with nested
resource patterns.  The URL hierarchy mirrors the ownership chain:

    /api/boards/                                      → board list/create
    /api/boards/{id}/                                 → board retrieve/update/delete
    /api/boards/{id}/full/                            → full board graph (custom @action)
    /api/boards/{board_pk}/items/                     → add item / list items
    /api/boards/{board_pk}/items/{id}/                → remove item
    /api/boards/{board_pk}/items/batch-coordinates/   → batch drag-and-drop save (@action)
    /api/boards/{board_pk}/connections/               → create connection
    /api/boards/{board_pk}/connections/{id}/          → delete connection
    /api/boards/{board_pk}/notes/                     → create note
    /api/boards/{board_pk}/notes/{id}/                → retrieve / update / delete note

Router Strategy
---------------
We use ``drf-nested-routers`` (``rest_framework_nested``) to generate the
``{board_pk}`` prefix automatically rather than hand-writing the patterns.

If ``drf-nested-routers`` is not yet in ``requirements.txt``, add it:
    pip install drf-nested-routers

Then in the top-level ``backend/backend/urls.py``, include this file::

    path("api/", include("board.urls")),
"""

from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers as nested_routers

from .views import (
    BoardConnectionViewSet,
    BoardItemViewSet,
    BoardNoteViewSet,
    DetectiveBoardViewSet,
)

# ── Root router ──────────────────────────────────────────────────────────────
# Handles   GET/POST  /api/boards/
#           GET       /api/boards/{id}/
#           PATCH     /api/boards/{id}/
#           DELETE    /api/boards/{id}/
#           GET       /api/boards/{id}/full/    ← custom @action
router = DefaultRouter()
router.register(
    prefix=r"boards",
    viewset=DetectiveBoardViewSet,
    basename="detective-board",
)

# ── Nested router: items ─────────────────────────────────────────────────────
# Parent lookup kwarg → board_pk
# Handles   POST   /api/boards/{board_pk}/items/
#           DELETE /api/boards/{board_pk}/items/{id}/
#           PATCH  /api/boards/{board_pk}/items/batch-coordinates/  ← @action
items_router = nested_routers.NestedDefaultRouter(
    parent_router=router,
    parent_prefix=r"boards",
    lookup="board",  # produces kwarg ``board_pk``
)
items_router.register(
    prefix=r"items",
    viewset=BoardItemViewSet,
    basename="board-item",
)

# ── Nested router: connections ───────────────────────────────────────────────
# Handles   POST   /api/boards/{board_pk}/connections/
#           DELETE /api/boards/{board_pk}/connections/{id}/
connections_router = nested_routers.NestedDefaultRouter(
    parent_router=router,
    parent_prefix=r"boards",
    lookup="board",
)
connections_router.register(
    prefix=r"connections",
    viewset=BoardConnectionViewSet,
    basename="board-connection",
)

# ── Nested router: notes ─────────────────────────────────────────────────────
# Handles   POST   /api/boards/{board_pk}/notes/
#           GET    /api/boards/{board_pk}/notes/{id}/
#           PATCH  /api/boards/{board_pk}/notes/{id}/
#           DELETE /api/boards/{board_pk}/notes/{id}/
notes_router = nested_routers.NestedDefaultRouter(
    parent_router=router,
    parent_prefix=r"boards",
    lookup="board",
)
notes_router.register(
    prefix=r"notes",
    viewset=BoardNoteViewSet,
    basename="board-note",
)

# ── Combined URL patterns ────────────────────────────────────────────────────
urlpatterns = [
    *router.urls,
    *items_router.urls,
    *connections_router.urls,
    *notes_router.urls,
]
