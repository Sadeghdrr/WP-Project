# Board Services Implementation Report

## 1. Permission Rules
### Create Access (`_can_create_board`)
| Actor | Condition |
|-------|----------|
| **Detective** | `user.role.name == "Detective"` |
| **Supervisor** (Sergeant / Captain / Police Chief) | `user.role.name` in `_SUPERVISOR_ROLES` |
| **System Admin / Superuser** | Always granted |
| **All other roles** (Cadet, Officer, Coroner, Base User, …) | **Denied → HTTP 403** |

Enforced in `BoardWorkspaceService.create_board` via `_can_create_board(requesting_user)` before any DB write.  Raises `PermissionDenied` (→ 403) for ineligible roles.
### Read Access (`_can_view_board`)
| Actor | Condition |
|-------|-----------|
| **Board's detective** | `board.detective_id == user.pk` |
| **Supervisor** (Sergeant / Captain / Police Chief) | User's role name is in `{"Sergeant", "Captain", "Police Chief"}` AND the user is assigned to the board's case (as detective, sergeant, captain, judge, creator, or approver) |
| **System Admin / Superuser** | Always granted |

### Write (Edit) Access (`_can_edit_board`)
Identical to read access — any user who can view the board can also modify it. The rationale is that supervisors reviewing a case may need to annotate the board with their own notes or connections.

### Note-Level Ownership
`update_note` and `delete_note` additionally verify that `requesting_user == note.created_by` (or the user is an admin). This prevents one detective from editing another's annotations even when both have board access.

### Board Deletion
Only the owning detective (`board.detective`) or a System Admin / superuser may delete a board.

---

## 2. Snapshot Schema Example

`GET /api/boards/{id}/full/` returns:

```json
{
  "id": 1,
  "case": 5,
  "detective": 3,
  "items": [
    {
      "id": 10,
      "content_type": 7,
      "object_id": 42,
      "content_object_summary": {
        "content_type_id": 7,
        "app_label": "evidence",
        "model": "biologicalevidence",
        "object_id": 42,
        "display_name": "Hair Sample #42",
        "detail_url": "/api/evidence/biological/42/"
      },
      "position_x": 120.5,
      "position_y": 300.0,
      "created_at": "2026-02-20T10:00:00Z",
      "updated_at": "2026-02-21T14:30:00Z"
    },
    {
      "id": 11,
      "content_type": 14,
      "object_id": 3,
      "content_object_summary": {
        "content_type_id": 14,
        "app_label": "board",
        "model": "boardnote",
        "object_id": 3,
        "display_name": "Witness saw suspect near crime scene",
        "detail_url": "/api/boards/notes/3/"
      },
      "position_x": 400.0,
      "position_y": 150.0,
      "created_at": "2026-02-20T11:00:00Z",
      "updated_at": "2026-02-20T11:00:00Z"
    }
  ],
  "connections": [
    {
      "id": 1,
      "from_item": 10,
      "to_item": 11,
      "label": "matches witness timeline",
      "created_at": "2026-02-20T12:00:00Z",
      "updated_at": "2026-02-20T12:00:00Z"
    }
  ],
  "notes": [
    {
      "id": 3,
      "title": "Witness saw suspect near crime scene",
      "content": "Mrs. Johnson reported seeing a tall man at 11:45 PM.",
      "created_by": 3,
      "created_at": "2026-02-20T11:00:00Z",
      "updated_at": "2026-02-20T11:00:00Z"
    }
  ],
  "created_at": "2026-02-20T09:00:00Z",
  "updated_at": "2026-02-21T14:30:00Z"
}
```

---

## 3. Optimization Strategy

`BoardWorkspaceService.get_full_board_graph` loads the entire board graph in a minimal number of DB queries:

| Query | What it fetches |
|-------|-----------------|
| **1** (main + `select_related`) | `DetectiveBoard` + `Case` + `User` (detective) — single JOIN |
| **2** (`prefetch_related` — items) | All `BoardItem` rows for the board, with `ContentType` via `select_related("content_type")` |
| **3** (`prefetch_related` — connections) | All `BoardConnection` rows, with `from_item` / `to_item` via `select_related` |
| **4** (`prefetch_related` — notes) | All `BoardNote` rows, with `created_by` via `select_related` |
| **5 … N** (GFK resolution) | One query **per distinct content-type** that appears in the items — e.g. one for `BiologicalEvidence`, one for `BoardNote`, etc. Uses `Model.objects.in_bulk(ids)` to batch-fetch all objects of each type in a single query |

The GFK resolution avoids N+1 by:
1. Grouping all `(content_type_id, object_id)` pairs by content type.
2. Calling `in_bulk()` once per content-type to fetch all referenced objects.
3. Patching the resolved objects onto each `BoardItem` as `_prefetched_content_object`.
4. The `GenericObjectRelatedField.to_representation` reads this cached attribute instead of triggering lazy `content_object` access.

**Total queries**: 4 + (number of distinct content types on the board) — typically 5–7 regardless of item count.

---

## 4. API Sequences

### 4.1 Adding a New Item

```bash
curl -X POST /api/boards/1/items/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content_object": {
      "content_type_id": 7,
      "object_id": 42
    },
    "position_x": 120.5,
    "position_y": 300.0
  }'
```

**Response** (HTTP 201):
```json
{
  "id": 10,
  "board": 1,
  "content_type": 7,
  "object_id": 42,
  "content_object_summary": {
    "content_type_id": 7,
    "app_label": "evidence",
    "model": "biologicalevidence",
    "object_id": 42,
    "display_name": "Hair Sample #42",
    "detail_url": "/api/evidence/biological/42/"
  },
  "position_x": 120.5,
  "position_y": 300.0,
  "created_at": "2026-02-23T10:00:00Z",
  "updated_at": "2026-02-23T10:00:00Z"
}
```

### 4.2 Batch Updating Positions

```bash
curl -X PATCH /api/boards/1/items/batch-coordinates/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"id": 10, "position_x": 200.0, "position_y": 350.0},
      {"id": 11, "position_x": 500.0, "position_y": 100.0}
    ]
  }'
```

**Response** (HTTP 200):
```json
[
  {
    "id": 10,
    "board": 1,
    "content_type": 7,
    "object_id": 42,
    "content_object_summary": { "..." : "..." },
    "position_x": 200.0,
    "position_y": 350.0,
    "created_at": "2026-02-23T10:00:00Z",
    "updated_at": "2026-02-23T10:05:00Z"
  },
  {
    "id": 11,
    "board": 1,
    "content_type": 14,
    "object_id": 3,
    "content_object_summary": { "..." : "..." },
    "position_x": 500.0,
    "position_y": 100.0,
    "created_at": "2026-02-23T10:01:00Z",
    "updated_at": "2026-02-23T10:05:00Z"
  }
]
```

### 4.3 Creating a Connection

```bash
curl -X POST /api/boards/1/connections/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "from_item": 10,
    "to_item": 11,
    "label": "matches witness timeline"
  }'
```

**Response** (HTTP 201):
```json
{
  "id": 1,
  "board": 1,
  "from_item": 10,
  "to_item": 11,
  "label": "matches witness timeline",
  "created_at": "2026-02-23T10:10:00Z",
  "updated_at": "2026-02-23T10:10:00Z"
}
```
