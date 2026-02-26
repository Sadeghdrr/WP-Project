# Detective Board Spike — Findings

> Technical spike for the Detective Board integration.
> Goal: de-risk frontend architecture and prove end-to-end data flow.

---

## Endpoints Used

| Action | Method | Path | Status |
|---|---|---|---|
| List boards | GET | `/api/boards/` | Implemented |
| Board detail | GET | `/api/boards/{id}/` | Implemented |
| **Full board graph** | GET | `/api/boards/{id}/full/` | Implemented — single-call load |
| Create board | POST | `/api/boards/` | Implemented |
| Add item (pin) | POST | `/api/boards/{board_pk}/items/` | Implemented |
| Remove item | DELETE | `/api/boards/{board_pk}/items/{id}/` | Implemented |
| **Batch coordinate update** | PATCH | `/api/boards/{board_pk}/items/batch-coordinates/` | Implemented — debounced on drag |
| Create connection | POST | `/api/boards/{board_pk}/connections/` | Implemented |
| Delete connection | DELETE | `/api/boards/{board_pk}/connections/{id}/` | Implemented |
| Create note | POST | `/api/boards/{board_pk}/notes/` | Implemented |
| Update note | PATCH | `/api/boards/{board_pk}/notes/{id}/` | Available but not wired in spike UI |
| Delete note | DELETE | `/api/boards/{board_pk}/notes/{id}/` | Available but not wired in spike UI |

---

## Payload Mapping Notes

### FullBoardState (GET .../full/)
```json
{
  "id": 1,
  "case": 5,
  "detective": 3,
  "items": [
    {
      "id": 1,
      "content_type": 7,
      "object_id": 42,
      "content_object_summary": {
        "content_type_id": 7,
        "app_label": "evidence",
        "model": "biologicalevidence",
        "object_id": 42,
        "display_name": "Fingerprint #42",
        "detail_url": "/api/evidence/biological/42/"
      },
      "position_x": 100.0,
      "position_y": 200.0,
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "connections": [
    { "id": 1, "from_item": 1, "to_item": 2, "label": "", "created_at": "...", "updated_at": "..." }
  ],
  "notes": [
    { "id": 1, "title": "Hypothesis", "content": "...", "created_by": 3, "created_at": "...", "updated_at": "..." }
  ],
  "created_at": "...",
  "updated_at": "..."
}
```

### Batch coordinate update (PATCH .../batch-coordinates/)
```json
{
  "items": [
    { "id": 1, "position_x": 150.0, "position_y": 250.0 },
    { "id": 2, "position_x": 400.0, "position_y": 100.0 }
  ]
}
```

### Board item create (POST .../items/)
```json
{
  "content_object": { "content_type_id": 7, "object_id": 42 },
  "position_x": 0.0,
  "position_y": 0.0
}
```

### Note create (POST .../notes/)
```json
{ "title": "My note", "content": "Details..." }
```
Backend auto-creates a BoardItem for this note via `BoardNoteService.create_note`.

### Connection create (POST .../connections/)
```json
{ "from_item": 1, "to_item": 2, "label": "" }
```

---

## What Worked

1. **Full board graph in one call** — The `GET .../full/` endpoint returns items, connections, and notes with resolved GenericForeignKey summaries. No N+1 waterfall needed.
2. **Batch coordinate saving** — `PATCH .../batch-coordinates/` accepts an array of `{id, position_x, position_y}` and uses `bulk_update` on the backend. Debounced client-side (800ms) for smooth drag-and-drop.
3. **Note auto-pinning** — Creating a note via `POST .../notes/` automatically creates a `BoardItem` (GFK) at position (0, 0). After refetch, the new note appears on the canvas.
4. **Connection create/delete** — Red lines between items can be created by dragging handles and deleted by clicking edges. Backend enforces uniqueness and same-board constraints.
5. **React Flow integration** — `@xyflow/react` handles node rendering, edge drawing, drag-and-drop, zoom/pan, and minimap out of the box. Custom nodes render content object summaries with type-specific icons.
6. **Export as PNG** — Using `html-to-image`, the viewport element can be captured and downloaded as a PNG. Works for basic scenarios.

---

## What Failed / Friction Points

1. **Board discovery by case** — The board list endpoint (`GET /api/boards/`) returns boards visible to the user but doesn't support filtering by `case_id` query parameter. Client-side filtering is needed after loading all boards. For production, a `?case=<id>` filter or a `get_or_create` endpoint per case would reduce round-trips.

2. **GenericForeignKey on item creation** — To add evidence or suspects as board items, the frontend needs to know the Django `ContentType` ID for each model. This is runtime-dependent and not exposed by a dedicated endpoint. A `GET /api/core/constants/` or content-type list endpoint would help. For the spike, note creation (which auto-pins) is the validated flow.

3. **content_object_summary null handling** — If the underlying object referenced by a `BoardItem` is deleted, `content_object_summary` returns `null`. The frontend handles this gracefully (shows `ct:X #Y`) but the UX is poor — orphaned items should be cleaned up or flagged.

4. **Export limitations** — `html-to-image` captures the visible viewport, not the full canvas. If the board is zoomed/panned, the export may crop content. For production, a server-side render or `getNodesBounds()` + custom viewport calculation is recommended.

5. **Board list serializer returns `detective` as integer ID** — The `DetectiveBoardListSerializer` returns `detective` as an FK integer, not a nested user object. Adequate for the spike (just display the ID), but production UI needs the detective's name.

6. **No `get_or_create` board endpoint exposed as REST** — The service layer has `get_or_create_board()`, but no view/URL route exposes it. The frontend must list → find → optionally create. Minor friction.

---

## Recommended Approach for Production Implementation

1. **Keep React Flow** — `@xyflow/react` is well-suited for this use case. It handles large node counts, custom nodes/edges, and has good TypeScript support.

2. **Add a `?case=<id>` filter** to the board list endpoint, or expose a dedicated `GET /api/boards/by-case/{case_id}/` endpoint.

3. **Expose ContentType mapping** — Either provide a lookup endpoint or embed content type IDs in the `GET .../full/` response metadata so the frontend can create items for specific evidence/suspect types without guessing IDs.

4. **Structured node types** — For production, create distinct React Flow node types for Notes, Evidence, Suspects, and Cases with appropriate visual styling and detail drill-through links.

5. **Optimistic updates** — Implement optimistic updates for drag-and-drop (already done for connections). This improves perceived performance.

6. **Server-side export** — For reliable "export as image" that captures the full board (not just the viewport), consider a headless browser render on the server, or use React Flow's `getNodesBounds()` + programmatic viewport adjustment before capture.

7. **Real-time sync** — If multiple users can view/edit the same board, consider WebSocket-based updates. The backend already has permission checks for supervisors viewing boards.
