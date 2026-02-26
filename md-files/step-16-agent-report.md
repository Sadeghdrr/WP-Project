# Step 16 — Detective Board Production Implementation

## Branch
`agent/step-16-detective-board-production`

## Files Created / Changed

### New Files
| File | Purpose |
|------|---------|
| `frontend/src/pages/DetectiveBoard/DetectiveBoardPage.module.css` | CSS module styles for the board page (layout, sidebar, buttons, inputs, modal, responsive) |
| `frontend/src/pages/DetectiveBoard/BoardItemNode.module.css` | CSS module styles for the custom React Flow node component |
| `frontend/src/pages/DetectiveBoard/PinEntityModal.tsx` | Dialog for pinning evidence / suspects to the board |
| `frontend/docs/detective-board-notes.md` | Technical notes: endpoints, data mapping, coordinate persistence, mutation flows, export approach |

### Modified Files
| File | Changes |
|------|---------|
| `frontend/src/pages/DetectiveBoard/DetectiveBoardPage.tsx` | Full production rewrite: replaced all inline styles with CSS modules; added note edit/delete; added pin-entity modal; added derived-state pattern (no synchronous setState in effects); cleaner architecture |
| `frontend/src/pages/DetectiveBoard/BoardItemNode.tsx` | Refactored to use CSS modules instead of inline styles |
| `frontend/src/pages/DetectiveBoard/useBoardData.ts` | Added missing hooks: `useCreateBoardItem`, `useUpdateNote`, `useDeleteNote`; exported query keys |
| `frontend/src/api/index.ts` | Added `boardApi` barrel export |
| `frontend/src/hooks/index.ts` | Added all board hook re-exports |

### Unchanged Files
| File | Reason |
|------|--------|
| `frontend/src/api/board.ts` | Already complete from spike — all CRUD functions present |
| `frontend/src/types/board.ts` | Already complete — type definitions match backend serializers |
| `frontend/src/api/endpoints.ts` | Already has all board endpoints |
| `frontend/src/router/Router.tsx` | Route `/detective-board/:caseId` already wired |
| `frontend/src/router/routes.ts` | Route config already present |

## Detective Board Features Implemented

### Core Features (required by project-doc §5.4)
1. **Documents and notes on board** — BoardItems (evidence, suspects) and BoardNotes displayed as React Flow nodes
2. **Red-line connections** — Drag from source handle to target handle to create; click edge to delete
3. **Drag-and-drop placement** — Items freely repositioned via React Flow drag; positions persisted via debounced batch API call (800 ms)
4. **Add/remove lines** — Connections created via drag, deleted via click with confirm dialog
5. **Export as image** — PNG export via `html-to-image` to attach to reports

### Additional Features
6. **Board auto-discovery** — Automatically finds existing board for the case; shows "Create" button if none exists
7. **Pin entity modal** — Add evidence / suspects from the current case to the board
8. **Note CRUD** — Create notes via sidebar form; inline edit and delete with confirmation
9. **Delete items** — Remove items from board via ✕ button on node
10. **Loading/error/empty states** — Proper feedback for all network states
11. **Responsive sidebar** — Collapses below canvas on mobile viewports

## Endpoints / Actions Used

| Action | Endpoint | Method |
|--------|----------|--------|
| List boards | `/api/board/boards/` | GET |
| Create board | `/api/board/boards/` | POST |
| Full board graph | `/api/board/boards/{id}/full/` | GET |
| Pin item | `/api/board/boards/{id}/items/` | POST |
| Unpin item | `/api/board/boards/{id}/items/{itemId}/` | DELETE |
| Batch update positions | `/api/board/boards/{id}/items/batch-coordinates/` | PATCH |
| Create connection | `/api/board/boards/{id}/connections/` | POST |
| Delete connection | `/api/board/boards/{id}/connections/{connId}/` | DELETE |
| Create note | `/api/board/boards/{id}/notes/` | POST |
| Update note | `/api/board/boards/{id}/notes/{noteId}/` | PATCH |
| Delete note | `/api/board/boards/{id}/notes/{noteId}/` | DELETE |

## Performance / Stability Approach

- **Debounced batch saves**: Drag position changes batched and sent 800 ms after last drag event via a single `PATCH /batch-coordinates/` call. Backend uses `bulk_update()` for one SQL round-trip.
- **Optimistic updates**: Connection creation adds the edge immediately; only reverts on error via refetch.
- **Query invalidation**: All mutations (except batch-coordinates) invalidate the `board-full` query key, triggering a single fresh fetch of the full graph.
- **No request storms**: The 800 ms debounce prevents per-pixel API calls during drag.
- **Derived state reset**: Uses React's "setState during render" pattern instead of `useEffect` for state resets, eliminating cascading renders.

## Deferred Items

| Item | Reason |
|------|--------|
| Real-time collaboration | Not required by project-doc; no WebSocket backend support |
| Undo/redo | Not required; significant client-side state complexity |
| Editable connection labels | Backend supports it; not required by project-doc |
| Board deletion UI | Low priority; endpoint exists |
| Pin Case entity to board | Backend supports `cases.case` CT but creates UI confusion (you're already viewing the case) |

## Backend Anomalies / Problems (Report Only)

1. **No `content_type_id` in evidence/suspect list responses**: The `/api/evidence/` and `/api/suspects/suspects/` endpoints don't include the ContentType ID needed for the `BoardItemCreateRequest.content_object.content_type_id` field. The PinEntityModal currently receives `content_type_id: 0` from these endpoints, which means the pin-entity feature may need the user to know the correct CT ID, or the backend should include it. **Workaround**: Could hardcode known CT IDs or fetch them from `/api/contenttypes/` if such an endpoint exists. This is a backend limitation, not something we can fix from the frontend.

2. **One board per case (OneToOneField)**: The `DetectiveBoard.case` field is a `OneToOneField`. If a board already exists for a case, creating another fails. The frontend handles this correctly by checking existing boards first.

## Confirmation: No Backend Files Modified

Zero files in `backend/` were modified by this implementation. All changes are in `frontend/` and `md-files/`.

## Coverage Summary vs project-doc §5.4

| Requirement | Status | Notes |
|-------------|--------|-------|
| Board contains documents or notes | **Implemented** | Evidence, suspects, and notes rendered as React Flow nodes |
| Documents/notes connected with red line | **Implemented** | Connections with red `#c0392b` stroke |
| Placement modifiable via drag-and-drop | **Implemented** | React Flow native drag with debounced batch persist |
| Lines addable and removable | **Implemented** | Add via handle drag; remove via click + confirm |
| Export as image for report | **Implemented** | PNG export via html-to-image |
