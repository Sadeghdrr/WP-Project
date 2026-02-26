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
| List boards | `/api/boards/` | GET |
| Create board | `/api/boards/` | POST |
| Full board graph | `/api/boards/{id}/full/` | GET |
| Pin item | `/api/boards/{id}/items/` | POST |
| Unpin item | `/api/boards/{id}/items/{itemId}/` | DELETE |
| Batch update positions | `/api/boards/{id}/items/batch-coordinates/` | PATCH |
| Create connection | `/api/boards/{id}/connections/` | POST |
| Delete connection | `/api/boards/{id}/connections/{connId}/` | DELETE |
| Create note | `/api/boards/{id}/notes/` | POST |
| Update note | `/api/boards/{id}/notes/{noteId}/` | PATCH |
| Delete note | `/api/boards/{id}/notes/{noteId}/` | DELETE |

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
| Pin Case entity to board | Backend supports `cases.case` CT but creates UI confusion (you're already viewing the case) |

## Fix Pass: Board-Case Integration (Step 16 Follow-Up)

### What Was Broken
1. **CaseDetailPage had no detective board section** — users had no way to see whether a board existed for a case, or to navigate to the board workspace.
2. **No create-board UI from case page** — board creation was only available inside the board workspace page itself, which required manual URL navigation.
3. **Boards created via API (backend) never appeared on the case page** — the case page had zero awareness of the board app.

### How It Was Fixed

#### New files / changes
| File | Change |
|------|--------|
| `frontend/src/pages/Cases/CaseDetailPage.tsx` | Added `DetectiveBoardSection` component: shows board info or "Create" button |
| `frontend/src/pages/DetectiveBoard/useBoardData.ts` | Added `useBoardForCase(caseId)` hook + `useDeleteBoard()` hook |
| `frontend/src/hooks/index.ts` | Exported `useBoardForCase` and `useDeleteBoard` |
| `frontend/docs/detective-board-notes.md` | Added case-board integration documentation |

#### Board-case integration summary
- `useBoardForCase(caseId)` reuses `useBoardsList()` (fetches `GET /api/boards/`) and derives the matching board via `boards.find(b => b.case === caseId)`.
- `DetectiveBoardSection` renders inside the CaseDetailPage grid, showing:
  - **If board exists**: Board ID, item count, connection count, created date, and "Open Detective Board" link → `/detective-board/:caseId`
  - **If no board**: "No detective board exists" message + "Create Detective Board" button (permission-gated)
  - **Loading/error states**: Proper feedback
  - **Permission gating**: Section hidden for users without `board.view_detectiveboard` or `board.add_detectiveboard`
- Board creation from case page: `POST /api/boards/` with `{ case: caseId }` → navigate to board workspace on success
- React Query invalidation ensures board list stays fresh after creation

#### Endpoints used
- `GET /api/boards/` — list boards → client-side filter by case
- `POST /api/boards/` — create board (payload `{ case: int }`, detective auto-assigned)
- `DELETE /api/boards/{id}/` — delete board (hook added, not yet wired to UI)

#### Data flow explanation
1. User opens `CaseDetailPage` for case #5
2. `useBoardForCase(5)` calls `GET /api/boards/` → returns all visible boards
3. Finds board where `board.case === 5` → shows board metadata + "Open" link
4. If no match → shows "Create" button → `POST /api/boards/` creates board → navigates to workspace
5. Workspace page (`/detective-board/5`) also calls `useBoardsList()` which hits the same React Query cache → immediate display

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
| Case page shows boards | **Implemented** | DetectiveBoardSection on CaseDetailPage |
| Board creation from case page | **Implemented** | "Create Detective Board" button with backend call |
| Board opening from case page | **Implemented** | "Open Detective Board" link navigates to workspace |
| Board list reflects backend truth | **Implemented** | React Query fetches from API on mount; no local-only storage |
---

## Infinite Loop Fix Pass (ReactFlow — Step 16 Bug Fix)

**Branch:** `agent/step-16-fix-reactflow-infinite-loop`

### Symptom

Navigating to `/detective-board/<id>` produced a "Maximum update depth exceeded" React crash immediately after mount. The board never rendered; instead the app threw continuously.

### Root Cause 1 — Unstable `handleDeleteItem` in sync effect dependency array (PRIMARY)

File: `frontend/src/pages/DetectiveBoard/DetectiveBoardPage.tsx`

```
// BEFORE (broken)
const handleDeleteItem = useCallback((itemId: number) => {
  if (!boardId) return;
  if (confirm("Remove this item from the board?")) deleteItemMut.mutate(itemId);
}, [boardId, deleteItemMut]);  // ← deleteItemMut is a new object reference every render

useEffect(() => {
  if (!boardState) return;
  setNodes(toNodes(boardState.items, handleDeleteItem));
  setEdges(toEdges(boardState.connections));
}, [boardState, handleDeleteItem, setNodes, setEdges]);
//                ↑ changes every render because handleDeleteItem changes every render
```

`useDeleteBoardItem(boardId)` calls React Query's `useMutation`, which returns a **fresh object reference on every render** whenever internal mutation state changes (isPending, isSuccess, etc.). Because `handleDeleteItem` listed `deleteItemMut` as a dependency, its identity was never stable. The sync effect listed `handleDeleteItem` as a dependency, so it fired on every render, called `setNodes()`, which caused ReactFlow's internal store to update, which triggered another re-render — creating an infinite loop.

### Root Cause 2 — setState-during-render in board discovery (SECONDARY)

```tsx
// BEFORE (broken) — setState called during render body
if (prevDiscovered !== discoveredId) {
  setPrevDiscovered(discoveredId);
  setBoardId(discoveredId);   // ← setState during render = immediate forced re-render
}
```

Calling `setState` unconditionally during the render body caused React to immediately queue another render, compounding Root Cause 1.

### Fix Applied

**1. Stabilise `handleDeleteItem` via refs:**

```tsx
// After — ref pattern: stable function identity forever
const boardIdRef = useRef<number | null>(boardId);
const deleteItemMutRef = useRef(deleteItemMut);

// Keep refs in sync after every commit (useLayoutEffect without deps)
useLayoutEffect(() => {
  boardIdRef.current = boardId;
  deleteItemMutRef.current = deleteItemMut;
});

const handleDeleteItem = useCallback((itemId: number) => {
  if (!boardIdRef.current) return;
  if (confirm("Remove this item from the board?")) {
    deleteItemMutRef.current.mutate(itemId);
  }
}, []); // ← intentionally empty; reads current values from refs at call-time
```

`useLayoutEffect` without a dependency array runs synchronously after every commit, keeping the refs up-to-date without triggering re-renders. `handleDeleteItem` now has a stable identity for the lifetime of the component.

**2. Replace board discovery state with pure derived value:**

```tsx
// After — pure derived value, no state, no useEffect, no cascading re-render
const discoveredId = boards?.find((b) => b.case === caseIdNum)?.id ?? null;
const boardId = discoveredId ?? createdBoardId;
// createdBoardId is only updated once, on createBoardMut.onSuccess
```

`discoveredId` is computed inline from the already-cached `boards` query result. `createdBoardId` is a stable state value changed only when a new board is successfully created. No effect runs; no intermediate state assignment occurs during render.

### New File — BoardErrorBoundary

`frontend/src/components/ui/BoardErrorBoundary.tsx` — React class component with `getDerivedStateFromError`. Wraps the detective board route so that any future runtime crash shows a recovery UI (Retry, Back to Case, All Cases links) instead of a blank white screen.

### Router Change

`frontend/src/router/Router.tsx` — Added `BoardWithErrorBoundary` functional component that reads `caseId` from `useParams` and renders `<BoardErrorBoundary caseId={caseId}><DetectiveBoardPage /></BoardErrorBoundary>`. The board route now uses this wrapper.

### Files Changed (Phase 3 — Infinite Loop Fix)

| File | Change |
|------|--------|
| `frontend/src/pages/DetectiveBoard/DetectiveBoardPage.tsx` | Ref pattern for `handleDeleteItem`; pure derived `boardId`; `useLayoutEffect` sync |
| `frontend/src/components/ui/BoardErrorBoundary.tsx` | **New** — error boundary class component |
| `frontend/src/router/Router.tsx` | Wrapped board route with `BoardWithErrorBoundary` |

### Verification

- `npx tsc --noEmit` → **0 errors**
- `npx eslint src/pages/DetectiveBoard/DetectiveBoardPage.tsx src/components/ui/BoardErrorBoundary.tsx src/router/Router.tsx` → **0 errors / 0 warnings**
- No backend files modified.

---

## Backend Fix: Auto-Resolve Evidence ContentType When `content_type_id` is NULL

**Branch:** (same branch — committed on top)

### Problem

`POST /api/boards/{board_pk}/items/` requires a `content_object` payload:

```json
{
  "content_object": { "content_type_id": <int>, "object_id": <int> },
  "position_x": 0.0,
  "position_y": 0.0
}
```

When the frontend sends `content_type_id: null` (i.e. "I know the object ID but not the CT pk"),
the previous `to_internal_value` implementation did:

```python
content_type_id = int(data["content_type_id"])  # int(None) → TypeError
```

The `TypeError` was caught by the broad `except (KeyError, TypeError, ValueError)` guard and raised
a generic `ValidationError`, blocking the request entirely.

### Serializer Modified

`backend/board/serializers.py` — `GenericObjectRelatedField.to_internal_value()`

The fix lives in the **field-level validation hook** of `GenericObjectRelatedField`, which is the
correct serializer-layer entry point for this logic (it runs before the serializer's `validate()`
method, is encapsulated within the field that owns the content-type semantics, and keeps
`BoardItemCreateSerializer` clean).

### Method Overridden

`GenericObjectRelatedField.to_internal_value(self, data)`

### How the Null Fallback Works

```python
raw_content_type_id = data.get("content_type_id")

if raw_content_type_id is None:
    # content_type_id was explicitly null → auto-resolve Evidence
    try:
        ct = ContentType.objects.get(app_label="evidence", model="evidence")
    except ContentType.DoesNotExist:
        raise serializers.ValidationError(
            "Evidence ContentType not found. Cannot auto-resolve content type."
        )
else:
    # Numeric value (correct or incorrect) → normal lookup path; no override
    content_type_id = int(raw_content_type_id)   # raises ValidationError on bad input
    ct = ContentType.objects.get(pk=content_type_id)
```

The key guard is `if raw_content_type_id is None` — the **exact Python `None`** sentinel. The check
is intentionally strict:

| Incoming `content_type_id` | Behaviour |
|---------------------------|-----------|
| `null` (JSON) / `None` (Python) | Auto-resolved to `evidence.Evidence` CT |
| `0` | Falls into `else` branch → `CT pk=0` lookup → `ContentType.DoesNotExist` → `ValidationError` |
| Any valid integer | Falls into `else` branch → used as-is |
| String / bad type | Falls into `else` branch → `int()` raises `ValueError` → `ValidationError` |

All downstream validation (allowed content types, object existence check) runs identically
regardless of which branch resolved `ct`.

### Confirmation: Service Layer Unchanged

- `backend/board/services.py` — **not touched**
- `backend/board/views.py` — **not touched**
- `backend/board/models.py` — **not touched**
- Zero changes outside `backend/board/serializers.py`

### Test Results

```
Ran 55 tests in 54.169s
OK
```

All 55 tests in `tests/test_board_and_suspects_flow.py` pass with no regression.
Scenarios covered: 6.1 through 6.8 (board creation, full state, item pinning, connections,
batch coordinates, sticky notes, declare suspects, sergeant review).