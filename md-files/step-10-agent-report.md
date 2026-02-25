# Step 10 — Detective Board Integration Spike (Agent Report)

**Branch:** `agent/step-10-detective-board-spike`
**Date:** 2026-02-25

---

## Files Created / Changed

| File | Action |
|---|---|
| `frontend/src/types/board.ts` | **Modified** — Aligned types with actual backend serializer payloads (added `ContentObjectSummary`, `FullBoardState`, `BatchCoordinateUpdateRequest`, `*WithBoard` variants; removed stale `DetectiveBoard` interface) |
| `frontend/src/types/index.ts` | **Modified** — Updated barrel re-exports for new board type names |
| `frontend/src/api/endpoints.ts` | **Modified** — Added board sub-resource endpoint helpers (`boardFull`, `boardItems`, `boardItemsBatchCoordinates`, `boardConnections`, `boardNotes`, etc.) |
| `frontend/src/api/board.ts` | **Created** — Board API functions: `listBoards`, `getBoardFull`, `createBoard`, `deleteBoard`, `createBoardItem`, `deleteBoardItem`, `batchUpdateCoordinates`, `createBoardConnection`, `deleteBoardConnection`, `createBoardNote`, `updateBoardNote`, `deleteBoardNote` |
| `frontend/src/pages/DetectiveBoard/useBoardData.ts` | **Created** — React Query hooks for all board mutations and queries |
| `frontend/src/pages/DetectiveBoard/BoardItemNode.tsx` | **Created** — Custom React Flow node component for board items with type icons and delete button |
| `frontend/src/pages/DetectiveBoard/DetectiveBoardPage.tsx` | **Modified** — Replaced placeholder with full spike implementation (React Flow canvas, drag-and-drop, connections, note creation, export) |
| `frontend/docs/board-spike-findings.md` | **Created** — Spike findings document |
| `frontend/package.json` | **Modified** — Added `@xyflow/react` and `html-to-image` dependencies |

---

## Board Endpoints Tested

| Endpoint | Tested In Spike |
|---|---|
| `GET /api/board/boards/` | Yes — board discovery/list |
| `GET /api/board/boards/{id}/full/` | Yes — full graph load |
| `POST /api/board/boards/` | Yes — create board for case |
| `POST /api/board/boards/{id}/items/` | Yes — API layer ready, not wired to UI button (note auto-pins) |
| `DELETE /api/board/boards/{id}/items/{id}/` | Yes — remove item via node X button |
| `PATCH /api/board/boards/{id}/items/batch-coordinates/` | Yes — debounced drag save |
| `POST /api/board/boards/{id}/connections/` | Yes — draw red line via handle drag |
| `DELETE /api/board/boards/{id}/connections/{id}/` | Yes — click edge to delete |
| `POST /api/board/boards/{id}/notes/` | Yes — sidebar form |
| `PATCH /api/board/boards/{id}/notes/{id}/` | API layer ready, UI not wired |
| `DELETE /api/board/boards/{id}/notes/{id}/` | API layer ready, UI not wired |

---

## Core Board Behaviors Validated

1. **Load full board graph** — Single GET returns items, connections, notes with GFK resolution. No N+1.
2. **Render nodes + edges** — React Flow renders BoardItems as draggable nodes and BoardConnections as red edges.
3. **Move nodes (drag-and-drop)** — Items can be freely repositioned on the canvas.
4. **Batch save coordinates** — Debounced PATCH sends all moved items in one `bulk_update` call.
5. **Create sticky note** — POST creates note + auto-pins as BoardItem at (0,0).
6. **Create connection (red line)** — Drag from source handle to target handle creates connection.
7. **Delete connection** — Click on edge triggers confirmation + DELETE.
8. **Delete item** — X button on node card triggers confirmation + DELETE.
9. **Export as PNG** — html-to-image captures viewport and triggers download. Works for basic cases.

---

## Backend Anomalies / Problems (Report Only — No Backend Changes Made)

1. **No case-based board filter** — `GET /api/board/boards/` does not support `?case=<id>` query param. The frontend must load all visible boards and filter client-side. This is suboptimal when the user has many boards.

2. **ContentType ID not discoverable** — To pin arbitrary evidence/suspects as BoardItems, the frontend needs the Django `ContentType.id` for each model type. No endpoint exposes this mapping. The spike works around this by relying on note creation (which auto-pins), but production will need a ContentType lookup or shortcut.

3. **`get_or_create_board` not exposed as REST** — The `BoardWorkspaceService.get_or_create_board()` method exists in the service layer but no view/URL routes to it. The frontend must do list → find → create as two separate calls.

4. **`DetectiveBoardListSerializer` returns `detective` as FK integer** — The list serializer returns `detective: <int>` instead of a nested user summary. Need to resolve user details separately.

5. **No board item list endpoint** — `BoardItemViewSet` doesn't have a `list` action. Items are only available via the `full/` endpoint. This is fine if the `full/` endpoint is always used, but limits partial updates.

6. **Orphaned BoardItems** — If a referenced content object (e.g., Evidence) is deleted, the BoardItem persists with `content_object_summary: null`. The backend does not cascade-clean these orphans.

---

## Risks for Final Board Implementation

| Risk | Severity | Mitigation |
|---|---|---|
| ContentType ID discovery for item pinning | **High** | Add a ContentType mapping endpoint or accept model-name shortcuts (e.g., `"evidence:42"`) |
| Export quality (viewport-only capture) | **Medium** | Use `getNodesBounds()` + programmatic zoom-to-fit before capture, or server-side render |
| Board canvas performance with many items (100+) | **Low** | React Flow handles up to ~1000 nodes well; virtualization available if needed |
| Real-time multi-user editing | **Medium** | WebSocket channel per board; backend already has supervisor read access |
| Board discovery UX (no case filter) | **Low** | Add `?case` filter or `get_or_create` endpoint; minor backend change |
| Orphaned items after evidence deletion | **Low** | Add signal/handler on evidence delete to clean up BoardItems |

---

## Confirmation: No Backend Files Modified

All changes are confined to `frontend/` and `md-files/`. Zero backend files were created or modified.

---

## Readiness Summary

### Validated Now (Spike-Proven)
- Full board graph load in a single API call
- Node rendering with React Flow (custom nodes, type icons)
- Drag-and-drop repositioning
- Batch coordinate persistence (debounced)
- Red line connections (create via handle drag, delete via click)
- Sticky note creation (auto-pins to board canvas)
- Board creation for a case
- Item/connection deletion
- PNG export (basic feasibility)

### Deferred to Full Implementation
- Complete RBAC UI gating (hide board for non-detective roles)
- Note editing / deletion in sidebar
- Pinning arbitrary evidence/suspects (requires ContentType lookup)
- Polished node styling per content type (distinct visuals for each evidence sub-type)
- Full-canvas export (zoom-to-fit before capture)
- Responsive layout / mobile support
- Loading skeleton states
- Undo/redo for board actions
- Connection labels editing

### Blocked by Backend Anomaly
- **Pinning external items**: Blocked by lack of ContentType ID discovery endpoint. Workaround: notes work; evidence pinning needs either a new endpoint or hard-coded ContentType IDs (fragile).
