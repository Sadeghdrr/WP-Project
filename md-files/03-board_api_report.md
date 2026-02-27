# Detective Board — API Design Report

**App:** `board`
**Branch:** `feat/board-api-drafts`
**Status:** Structural Draft (business logic not yet implemented)

---

## 1. Endpoint Reference Table

| # | HTTP Method | URL | Purpose | Access Level |
|---|-------------|-----|---------|--------------|
| 1 | `GET` | `/api/boards/` | List all boards visible to the requesting user (filtered by role) | Detective, Sergeant, Captain, Police Chief, Admin |
| 2 | `POST` | `/api/boards/` | Create a new `DetectiveBoard` for a given Case | Detective, Admin |
| 3 | `GET` | `/api/boards/{id}/` | Retrieve lightweight board metadata (no nested items) | Detective (owner), Sergeant, Captain, Police Chief, Admin |
| 4 | `PATCH` | `/api/boards/{id}/` | Partial update of board metadata | Detective (owner), Admin |
| 5 | `DELETE` | `/api/boards/{id}/` | Delete a board and all its child records (CASCADE) | Detective (owner), Admin |
| 6 | `GET` | `/api/boards/{id}/full/` | **Full Board State** — returns board + items + connections + notes in one payload | Detective (owner), Sergeant, Captain, Police Chief, Admin |
| 7 | `POST` | `/api/boards/{board_pk}/items/` | Add a new pin to the board (accepts `content_type_id` + `object_id`) | Detective (owner), Admin |
| 8 | `DELETE` | `/api/boards/{board_pk}/items/{id}/` | Remove a pin from the board | Detective (owner), Admin |
| 9 | `PATCH` | `/api/boards/{board_pk}/items/batch-coordinates/` | **Batch coordinate update** — repositions multiple items in one request (drag-and-drop save) | Detective (owner), Admin |
| 10 | `POST` | `/api/boards/{board_pk}/connections/` | Create a red-line connection between two `BoardItem`s | Detective (owner), Admin |
| 11 | `DELETE` | `/api/boards/{board_pk}/connections/{id}/` | Remove a red-line connection | Detective (owner), Admin |
| 12 | `POST` | `/api/boards/{board_pk}/notes/` | Create a sticky note on the board | Detective (owner), Admin |
| 13 | `GET` | `/api/boards/{board_pk}/notes/{id}/` | Retrieve a single sticky note | Detective (owner), Sergeant, Captain, Admin |
| 14 | `PATCH` | `/api/boards/{board_pk}/notes/{id}/` | Partially update a sticky note's title/content | Note creator, Admin |
| 15 | `DELETE` | `/api/boards/{board_pk}/notes/{id}/` | Delete a sticky note | Note creator, Admin |

> **Access Levels** are enforced in `services.py`, not in views or serializers.
> All endpoints require `IsAuthenticated`.

---

## 2. GenericForeignKey Handling in DRF Serializers

### 2.1 The Problem

Django's `GenericForeignKey` is a virtual attribute composed of two concrete fields:

```
content_type  →  FK to django_content_type table
object_id     →  PositiveIntegerField
content_object → resolved Python object (no DB column)
```

DRF's standard `ModelSerializer` **cannot** serialize `content_object` automatically because it has no dedicated database column and no field mapping. Additionally, a naïve implementation would trigger an N+1 query: for a board with 30 items, each `content_object` access would fire a separate `SELECT` to fetch the referenced object.

### 2.2 Our Solution: `GenericObjectRelatedField`

We implement a custom `serializers.Field` subclass that handles both directions:

#### Read Path (Serialization)

```
BoardItem.content_object  →  GenericObjectRelatedField.to_representation()
```

1. Calls `ContentType.objects.get_for_model(value)` to retrieve the content type record.
2. Builds a compact summary dict:

```json
{
  "content_type_id": 7,
  "app_label": "evidence",
  "model": "biologicalevidence",
  "object_id": 42,
  "display_name": "Hair Sample #42",
  "detail_url": "/api/evidence/biological/42/"
}
```

The `display_name` is produced by `str(value)` — each model's `__str__` is already defined.  
The `detail_url` is built from a hardcoded mapping dict `{"evidence.biologicalevidence": "/api/evidence/biological/", ...}` defined inside the field class.

**N+1 Prevention:** The service layer (`BoardWorkspaceService.get_full_board_graph`) pre-fetches all `content_object` instances via `prefetch_related_objects(board.items.all(), "content_object")` before the serializer runs. This collapses what would be 30+ individual `SELECT` calls into a small number of bulk `SELECT … WHERE id IN (…)` calls — one per unique content type present on the board.

#### Write Path (Deserialization)

```json
{ "content_type_id": 7, "object_id": 42 }
→ GenericObjectRelatedField.to_internal_value()
→ {"content_type": <ContentType pk=7>, "object_id": 42}
```

Validation steps:
1. Assert the payload is a `dict` with both keys.
2. Resolve `ContentType.objects.get(pk=content_type_id)` — raises `HTTP 400` on `DoesNotExist`.
3. Check `"app_label.model"` against the `ALLOWED_CONTENT_TYPES` frozenset — prevents clients from linking arbitrary models (e.g., `auth.user`) to a board.
4. Call `ct.model_class().objects.filter(pk=object_id).exists()` — raises `HTTP 400` if the target object does not exist.
5. Return `{"content_type": ct, "object_id": object_id}` for the service layer to use.

### 2.3 Why Not `django-polymorphic` or `drf-writable-nested`?

| Option | Why Rejected |
|--------|-------------|
| `django-polymorphic` | Requires all linked models to inherit from a common `PolymorphicModel` base — incompatible with the existing multi-table evidence hierarchy |
| `drf-writable-nested` | Handles FK nesting, not GFK; adds a transitive write path we don't need |
| Raw `content_type` + `object_id` fields | Forces the frontend to know DRF's internal ContentType IDs; brittle |
| **`GenericObjectRelatedField` (chosen)** | Self-contained, auditable, compatible with the existing model structure, and keeps all resolution logic in one class |

---

## 3. Batch Coordinate Update — Technical Design

### 3.1 The Problem

A detective board may contain dozens of items. When the user finishes a canvas rearrangement (drag-and-drop session), the frontend needs to persist the new positions for *every moved item*. A naïve implementation would issue one `UPDATE boards_boarditem SET … WHERE id = ?` per item — 30 items = 30 round-trips.

### 3.2 The Solution: `bulk_update` + Debounced Frontend Calls

#### Backend — `BoardItemService.update_batch_coordinates`

```
Input:  [{"id": 1, "position_x": 100.0, "position_y": 200.0}, ...]
```

**Algorithm:**

```
1.  Guard: verify requesting_user has write access to board.
2.  ids = [d["id"] for d in items_data]
3.  items = list(BoardItem.objects.filter(board=board, pk__in=ids))
4.  Guard: assert len(items) == len(ids)
           → catches cross-board ID injection attacks
5.  item_map = {item.id: item for item in items}  (O(n) dict build)
6.  For each d in items_data:
        item_map[d["id"]].position_x = d["position_x"]
        item_map[d["id"]].position_y = d["position_y"]
7.  BoardItem.objects.bulk_update(items, fields=["position_x", "position_y"])
    → Django issues a SINGLE UPDATE … CASE WHEN … statement
8.  Return items
```

**Database hit count: 2**
- `SELECT … WHERE board_id = ? AND id IN (…)` — fetch items to update
- `UPDATE boards_boarditem SET position_x = CASE WHEN id=1 THEN … … END WHERE id IN (…)` — one bulk write

Compared to the naïve per-item approach: **O(1) queries vs. O(n) queries**.

#### Serializer Validation — `BatchCoordinateUpdateSerializer`

Before the service receives the data, the serializer validates:
- Each element has `id` (int), `position_x` (float), `position_y` (float).
- No duplicate `id` values exist within the batch (prevents accidental double-write).

```json
{
  "items": [
    {"id": 1, "position_x": 100.0, "position_y": 200.0},
    {"id": 2, "position_x": 350.5, "position_y": 80.0}
  ]
}
```

#### Frontend Contract (for Next.js)

The frontend canvas MUST:
1. **Debounce** this endpoint — send one request on `mouseup` / `dragend`, not on every `mousemove`.
2. Batch *all* moved items into a single payload per gesture, not one request per item.
3. Invalidate the local board state cache after a successful `200 OK` response.

This combination of a single-query backend and a debounced, batched frontend call means that even a heavily-loaded board with 50+ repositioned items results in exactly **2 database queries per save gesture**.

---

## 4. File Inventory

| File | Role |
|------|------|
| `backend/board/models.py` | Existing data models (unchanged) |
| `backend/board/serializers.py` | Request/Response serializers + `GenericObjectRelatedField` |
| `backend/board/services.py` | Fat service layer — all business logic, queries, guards |
| `backend/board/views.py` | Thin ViewSets — validate → call service → return Response |
| `backend/board/urls.py` | DRF router + `drf-nested-routers` URL registration |
| `md-files/board_api_report.md` | This document |

---

## 5. Dependencies

`drf-nested-routers==0.95.0` is already present in `backend/requirements.txt`.
This package is required by `board/urls.py` for the `NestedDefaultRouter` pattern.
