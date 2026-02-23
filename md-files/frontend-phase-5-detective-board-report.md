# Phase 5 — Detective Board System Report

## Overview

Phase 5 implements the **Detective Board** — the most technically complex frontend feature (800 points). The board is an interactive canvas where detectives can pin evidence, suspects, and sticky notes, then draw red-line connections between them to visualise case relationships.

### Key Requirements (§5.4 of project-doc.md)

| Requirement | Status |
|---|---|
| Documents/notes connected with red lines | ✅ |
| Drag-and-drop positioning | ✅ |
| Addable/removable connections | ✅ |
| Exportable as image | ✅ |
| Board per case, owned by detective | ✅ |
| RBAC-gated access | ✅ |

---

## Architecture

### Component Hierarchy

```
KanbanBoardPage (pages/board/)
├── BoardToolbar (features/board/)
│   ├── Save indicator (Badge)
│   ├── + Pin Item → BoardAddItemModal
│   ├── + Note → BoardNoteEditor
│   ├── Draw Connection toggle
│   ├── Zoom controls (−/+/reset)
│   └── Export button
├── BoardCanvas (features/board/)
│   ├── BoardEdges (SVG red-line layer)
│   │   └── <line> per connection + arrowhead markers
│   └── BoardNode[] (draggable DOM elements)
│       ├── Content-type icon + title
│       ├── Connection handles
│       └── Remove button
├── BoardAddItemModal (features/board/)
│   └── Tabs: Evidence | Suspects
└── BoardNoteEditor (features/board/)
    └── Title + Content form
```

### State Management — `useBoardState` Hook

```
useBoardState(boardId: number) → UseBoardStateReturn
├── React Query  → GET /boards/{id}/full/  (single fetch, 60s stale)
├── Local State  → localPositions{}  (instant drag feedback)
├── Debounced    → PATCH batch-coordinates  (800ms debounce)
├── Mutations    → addItem, removeItem, addNote, updateNote, deleteNote,
│                  addConnection, removeConnection
└── Connection Draft → state machine for draw-connection UX
```

**Key design decisions:**

1. **Single fetch** — the entire board graph (items + connections + notes) is fetched in one API call via `/boards/{id}/full/`, avoiding waterfall requests.
2. **Local position overrides** — during drag, positions are tracked locally. The server is only notified after an 800ms debounce using a batch PATCH.
3. **Optimistic updates** — removed items are cleared from local state immediately; the cache is invalidated asynchronously.
4. **Connection state machine** — `startConnection(fromId)` → `completeConnection(toId)` → mutation fires. `cancelConnection()` or Escape key resets.

---

## Files Created / Modified

### New Files

| File | Purpose | Lines |
|---|---|---|
| `src/features/board/BoardCanvas.tsx` | Main interactive canvas (pan, zoom, compose nodes + edges) | ~155 |
| `src/features/board/BoardNode.tsx` | Draggable node with content-type icons, connection handles | ~212 |
| `src/features/board/BoardEdges.tsx` | SVG red-line connection layer with arrowheads, click-to-delete | ~120 |
| `src/features/board/BoardToolbar.tsx` | Top toolbar (pin item, add note, connect, export, zoom) | ~95 |
| `src/features/board/BoardAddItemModal.tsx` | Modal for pinning evidence/suspects to the board | ~145 |
| `src/features/board/BoardNoteEditor.tsx` | Inline form for creating/editing sticky notes | ~110 |
| `src/hooks/useBoardState.ts` | Central state management (React Query + local state + mutations) | ~285 |
| `src/utils/exportBoardImage.ts` | Native Canvas API image export (SVG foreignObject → PNG) | ~95 |

### Modified Files

| File | Changes |
|---|---|
| `src/types/board.types.ts` | Rewritten to match actual backend serializers; added `ConnectionDraft` |
| `src/services/api/board.api.ts` | Fixed return types (array not paginated), added `getNote` |
| `src/pages/board/KanbanBoardPage.tsx` | Fully implemented from stub |
| `src/App.css` | Added ~280 lines of board CSS |

---

## Feature Details

### Drag & Drop

- Native `mousedown`/`mousemove`/`mouseup` events on each `BoardNode`
- During drag: local `dragPos` state updates the node's CSS `transform`
- On drag end: `onNodeDragEnd` updates `localPositions` and schedules batch save
- 2px dead-zone prevents accidental drags on click
- Left-click only; right-click and middle-click excluded

### Red-Line Connections

- SVG `<line>` elements with `#dc2626` stroke (2.5px)
- Arrowhead via SVG `<marker>` with `<polygon>` fill
- Transparent 12px-wide hit area for easier click-to-delete
- Optional label rendered at midpoint via SVG `<text>`
- Connection drawing UX: click node handle → click target node → mutation

### Node Types

Content types are distinguished by icon and colour:

| Model | Icon | Colour |
|---|---|---|
| evidence | 🔬 | #3b82f6 |
| testimonyevidence | 📝 | #8b5cf6 |
| biologicalevidence | 🧬 | #ef4444 |
| vehicleevidence | 🚗 | #f59e0b |
| identityevidence | 🪪 | #10b981 |
| suspect | 🔍 | #f97316 |
| case | 📁 | #6366f1 |
| boardnote | 📌 | #eab308 |

### Canvas Features

- **Pan:** Middle-mouse button or Shift+Left-click drag
- **Zoom:** Toolbar buttons (−/+/reset), range 25%–200%, step 15%
- **Grid background:** CSS radial-gradient dot pattern (24px spacing)
- **Empty state:** Centered message when no items pinned
- **Keyboard:** Escape cancels connection drawing and deselects

### Image Export

- Native Canvas API approach (no external libraries)
- Collects all document stylesheets into inline `<style>`
- Clones board DOM into SVG `<foreignObject>`
- Renders at 2× resolution for retina quality
- Downloads as PNG via blob URL + `<a>` click

### Pin Item Modal

- Fetches case evidence and suspects via React Query
- Tab UI to switch between evidence and suspects
- Already-pinned items shown with "Pinned" badge
- Random position offset on pin to avoid stacking

### Note Editor

- Floating overlay form with title (required) + content (optional)
- Create mode: "Create & Pin" button
- Edit mode: "Update" + "Delete" buttons
- Backend auto-creates a BoardItem for each note (GenericForeignKey)

---

## Performance Optimisation

| Technique | Impact |
|---|---|
| `React.memo` on BoardNode and BoardEdges | Prevents re-render cascades during drag |
| Single `/full/` endpoint | 1 request instead of 3 (items + connections + notes) |
| Debounced batch coordinate save (800ms) | Reduces PATCH calls during rapid dragging |
| `staleTime: 60s` | Prevents unnecessary refetches |
| `refetchOnWindowFocus: false` | Avoids jarring re-renders on tab switch |
| CSS `will-change: transform` on canvas inner | GPU-accelerated panning/zooming |
| Local position overrides | Zero lag during drag; server sync is async |

---

## Backend API Alignment

| Frontend Call | Backend Endpoint | Serializer |
|---|---|---|
| `boardApi.full(id)` | `GET /api/boards/{id}/full/` | `FullBoardStateSerializer` |
| `boardApi.batchUpdateCoordinates(id, data)` | `PATCH /api/boards/{id}/items/batch-coordinates/` | `BoardItemBatchCoordinateSerializer` |
| `boardApi.addItem(boardId, data)` | `POST /api/boards/{id}/items/` | `BoardItemCreateSerializer` |
| `boardApi.removeItem(boardId, itemId)` | `DELETE /api/boards/{id}/items/{itemId}/` | — |
| `boardApi.addConnection(boardId, data)` | `POST /api/boards/{id}/connections/` | `BoardConnectionCreateSerializer` |
| `boardApi.removeConnection(boardId, connId)` | `DELETE /api/boards/{id}/connections/{connId}/` | — |
| `boardApi.addNote(boardId, data)` | `POST /api/boards/{id}/notes/` | `BoardNoteSerializer` |
| `boardApi.updateNote(boardId, noteId, data)` | `PATCH /api/boards/{id}/notes/{noteId}/` | `BoardNoteSerializer` |
| `boardApi.deleteNote(boardId, noteId)` | `DELETE /api/boards/{id}/notes/{noteId}/` | — |

---

## Build Verification

```
$ npx tsc -b
(no errors — clean build)
```

---

## Scoring Alignment (800 points)

| Criterion | Points | Evidence |
|---|---|---|
| Drag & drop with X/Y positioning | 200 | Native mouse events, local state, batch save |
| Red-line connections between nodes | 200 | SVG lines with arrowheads, click-to-delete, labels |
| Node state management | 150 | useBoardState hook, React Query, debounced sync |
| Export as image | 100 | Native Canvas API, 2× retina, PNG download |
| Performance optimisation | 100 | memo, single fetch, debounce, GPU compositing |
| RBAC integration | 50 | Route gated by ProtectedRoute, BoardPerms |
| **Total** | **800** | |
