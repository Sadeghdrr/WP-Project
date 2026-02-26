# Detective Board — Frontend Technical Notes

## Endpoints Used

| # | Endpoint | Method | Purpose |
|---|----------|--------|---------|
| 1 | `GET /api/board/boards/` | GET | List all boards visible to the user |
| 2 | `POST /api/board/boards/` | POST | Create board for a case (`{ case: int }`) |
| 3 | `GET /api/board/boards/{id}/full/` | GET | Full board graph (items + connections + notes) |
| 4 | `POST /api/board/boards/{boardId}/items/` | POST | Pin a content object (evidence, suspect, etc.) to the board |
| 5 | `DELETE /api/board/boards/{boardId}/items/{id}/` | DELETE | Unpin an item from the board |
| 6 | `PATCH /api/board/boards/{boardId}/items/batch-coordinates/` | PATCH | Batch update X/Y positions after drag-and-drop |
| 7 | `POST /api/board/boards/{boardId}/connections/` | POST | Create a red-line connection between two items |
| 8 | `DELETE /api/board/boards/{boardId}/connections/{id}/` | DELETE | Remove a connection |
| 9 | `POST /api/board/boards/{boardId}/notes/` | POST | Create a sticky note (auto-pinned by backend) |
| 10 | `PATCH /api/board/boards/{boardId}/notes/{id}/` | PATCH | Update note title/content |
| 11 | `DELETE /api/board/boards/{boardId}/notes/{id}/` | DELETE | Delete a note (backend cleans up the auto-pinned item) |

## Board Data Mapping Strategy

- The board is fetched as a **single full graph** via `GET /full/` — returns items, connections, and notes together.
- Items use Django's `GenericForeignKey` to reference any entity (Evidence, Suspect, Case, BoardNote). Each item carries a `content_object_summary` with `app_label`, `model`, `display_name`, etc.
- React Flow nodes are mapped 1:1 from `BoardItem[]` — the item ID becomes the node ID.
- React Flow edges are mapped 1:1 from `BoardConnection[]` — using `from_item`/`to_item` as source/target node IDs.
- Notes exist both as sidebar cards and as board items (the backend auto-creates a `BoardItem` pointing to the note via GFK).

## Coordinate Persistence Strategy

- **Debounced batch save**: Position changes from dragging are collected in a `Map<nodeId, {x, y}>` via a `useRef`.
- After 800 ms of idle (no new drag events), a single `PATCH /batch-coordinates/` request sends all pending moves.
- The backend uses `bulk_update()` for a single SQL round-trip.
- No query invalidation on success — React Flow's local node positions are already correct (optimistic).
- Only show error toast if the save fails.

## Mutation Flows

### Board Discovery
1. `GET /boards/` → find board where `board.case === caseId`
2. If found → fetch full state; if not → show "Create Board" button
3. `POST /boards/` with `{ case: caseId }` → set boardId → fetch full state

### Pin Entity
1. Open modal → fetch evidence (`GET /evidence/?case=X`) and suspects (`GET /suspects/suspects/?case=X`)
2. Filter out already-pinned items (comparing `content_type:object_id`)
3. User selects one → `POST /items/` with `{ content_object: { content_type_id, object_id }, position_x, position_y }`
4. On success → close modal, invalidate full board query → canvas updates

### Notes
- **Create**: Sidebar form → `POST /notes/` with `{ title, content }` → invalidate full board query
- **Edit**: Inline editing in sidebar → `PATCH /notes/{id}/` with `{ title, content }`
- **Delete**: Confirm dialog → `DELETE /notes/{id}/` → invalidate full board query

### Connections
- **Create**: Drag from source handle to target handle → optimistically add edge → `POST /connections/` with `{ from_item, to_item, label: "" }`
- **Delete**: Click on red line → confirm dialog → `DELETE /connections/{id}/` → invalidate full board query

### Item Deletion
- Click ✕ on node card → confirm dialog → `DELETE /items/{id}/` → invalidate full board query

## Export Approach

- **Client-side PNG export** using `html-to-image` (`toPng()`).
- Targets the React Flow viewport element (`.react-flow__viewport`).
- Downloads as `detective-board-case-{caseId}.png`.
- This satisfies the project-doc requirement: "it must be possible to export it as an image so the Detective can attach it to their report."

## Deferred Enhancements

| Feature | Reason |
|---------|--------|
| Real-time collaboration | Not required by project-doc; backend has no WebSocket support |
| Undo/redo | Not required; would need significant client-side state machinery |
| Connection labels (editable) | Backend supports `label` field, but not required by project-doc; kept empty for now |
| Board deletion from UI | Endpoint exists but not wired — low priority |
| Pinning the Case itself to the board | Backend supports it (via `cases.case` ContentType) but not shown in pin modal to avoid confusion |
