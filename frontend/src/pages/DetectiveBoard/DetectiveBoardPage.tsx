/**
 * DetectiveBoardPage — Production detective board workspace.
 *
 * Interactive canvas where Detectives place evidence, suspects, and notes at
 * arbitrary X/Y positions and draw "red lines" (connections) between them.
 *
 * Route: /detective-board/:caseId
 *
 * Features:
 *   - Board auto-discovery: finds (or creates) the board for the given case
 *   - React Flow canvas with draggable custom nodes and red edge connections
 *   - Debounced batch-coordinate save after drag (800 ms)
 *   - Create/delete notes in sidebar (backend auto-pins note → BoardItem)
 *   - Pin evidence / suspects via "Add Item" modal
 *   - Delete items from board (X button on node)
 *   - Create/delete connections by dragging handles / clicking edge
 *   - Export canvas as PNG (html-to-image)
 *   - Loading/error/empty states, responsive sidebar collapse
 */

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  type Node,
  type Edge,
  type OnConnect,
  type NodeChange,
  type Connection,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { toPng } from "html-to-image";

import { BoardItemNode, type BoardItemNodeData } from "./BoardItemNode";
import PinEntityModal from "./PinEntityModal";
import {
  useBoardsList,
  useBoardFull,
  useCreateBoard,
  useCreateBoardItem,
  useCreateNote,
  useUpdateNote,
  useDeleteNote,
  useCreateConnection,
  useDeleteConnection,
  useDeleteBoardItem,
  useBatchSaveCoordinates,
} from "./useBoardData";
import type { BoardItem, BoardConnection, BoardNote } from "../../types/board";
import { ErrorState, LoadingSpinner } from "../../components/ui";
import css from "./DetectiveBoardPage.module.css";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const NODE_TYPES = { boardItem: BoardItemNode };
const DEBOUNCE_MS = 800;
const RED = "#c0392b";
const DEFAULT_EDGE_OPTS = { style: { stroke: RED, strokeWidth: 2 } };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function toNodes(
  items: BoardItem[],
  onDelete?: (id: number) => void,
): Node[] {
  return items.map((item) => ({
    id: String(item.id),
    type: "boardItem",
    position: { x: item.position_x, y: item.position_y },
    data: { boardItem: item, onDelete } satisfies BoardItemNodeData,
  }));
}

function toEdges(connections: BoardConnection[]): Edge[] {
  return connections.map((c) => ({
    id: `conn-${c.id}`,
    source: String(c.from_item),
    target: String(c.to_item),
    sourceHandle: "bottom",
    targetHandle: "top",
    data: { connectionId: c.id },
  }));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DetectiveBoardPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const caseIdNum = caseId ? Number(caseId) : null;

  // ── Board discovery ─────────────────────────────────────────────
  // boardId is DERIVED from boards list query — no extra state needed.
  // createdBoardId is the only real state: set once when the user creates
  // a brand-new board and the list hasn't refetched yet to include it.
  const { data: boards, isLoading: boardsLoading, error: boardsError } =
    useBoardsList();
  const [createdBoardId, setCreatedBoardId] = useState<number | null>(null);
  const createBoardMut = useCreateBoard();

  // Pure derivation during render — no setState, no useEffect needed.
  const discoveredId = boards?.find((b) => b.case === caseIdNum)?.id ?? null;
  const boardId = discoveredId ?? createdBoardId;

  // ── Full board data ─────────────────────────────────────────────
  const {
    data: boardState,
    isLoading: boardLoading,
    error: boardError,
    refetch: refetchBoard,
  } = useBoardFull(boardId);

  // ── React Flow state ────────────────────────────────────────────
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const reactFlowRef = useRef<HTMLDivElement>(null);

  // ── Mutations ───────────────────────────────────────────────────
  const createBoardItemMut = useCreateBoardItem(boardId ?? 0);
  const createNoteMut = useCreateNote(boardId ?? 0);
  const updateNoteMut = useUpdateNote(boardId ?? 0);
  const deleteNoteMut = useDeleteNote(boardId ?? 0);
  const createConnMut = useCreateConnection(boardId ?? 0);
  const deleteConnMut = useDeleteConnection(boardId ?? 0);
  const deleteItemMut = useDeleteBoardItem(boardId ?? 0);
  const batchSaveMut = useBatchSaveCoordinates(boardId ?? 0);

  // ── UI state ────────────────────────────────────────────────────
  const [saveStatus, setSaveStatus] = useState("");
  const [exportStatus, setExportStatus] = useState("");
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");
  const [editingNote, setEditingNote] = useState<BoardNote | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [showPinModal, setShowPinModal] = useState(false);

  // ── Content type cache ──────────────────────────────────────────
  // Build a mapping of model name → content_type_id from existing board items.
  // Persisted in a ref so it survives item removal (once seen, always known).
  const ctCacheRef = useRef<Map<string, number>>(new Map());
  useEffect(() => {
    if (!boardState) return;
    for (const item of boardState.items) {
      const summary = item.content_object_summary;
      if (summary) {
        ctCacheRef.current.set(summary.model, summary.content_type_id);
      }
    }
  }, [boardState]);

  // Set of note IDs currently pinned to the board
  const pinnedNoteIds = useMemo(() => {
    if (!boardState) return new Set<number>();
    const ids = new Set<number>();
    for (const item of boardState.items) {
      const summary = item.content_object_summary;
      if (summary && summary.model === "boardnote") {
        ids.add(summary.object_id);
      }
    }
    return ids;
  }, [boardState]);

  // Handler: re-pin a note that was previously removed from the board
  const handlePinNote = useCallback(
    (noteId: number) => {
      const ctId = ctCacheRef.current.get("boardnote") ?? null;
      createBoardItemMut.mutate({
        content_object: { content_type_id: ctId, object_id: noteId },
        position_x: 0,
        position_y: 0,
      });
    },
    [createBoardItemMut],
  );

  // ── Sync backend → React Flow ───────────────────────────────────
  //
  // FIX: deleteItemMut (useMutation result) is a new object reference every
  // render, so any useCallback/useEffect that lists it as a dep fires every
  // render.  We break the chain by storing boardId and deleteItemMut in refs
  // and giving handleDeleteItem an empty dependency array — making it a
  // forever-stable function identity.
  //
  // Without this: deleteItemMut changes → handleDeleteItem changes →
  //   sync effect fires → setNodes called → React Flow updates store →
  //   re-render → deleteItemMut changes → LOOP.
  const boardIdRef = useRef<number | null>(boardId);
  const deleteItemMutRef = useRef(deleteItemMut);

  // Keep refs in sync after every render (useLayoutEffect without deps = runs
  // synchronously after every DOM update, before the browser paints).
  // This guarantees the refs are always current by the time any event handler
  // is invoked, without triggering additional renders.
  useLayoutEffect(() => {
    boardIdRef.current = boardId;
    deleteItemMutRef.current = deleteItemMut;
  });

  // Stable forever — reads current values from refs at call-time.
  const handleDeleteItem = useCallback((itemId: number) => {
    if (!boardIdRef.current) return;
    if (confirm("Remove this item from the board?")) {
      deleteItemMutRef.current.mutate(itemId);
    }
  }, []); // ← intentionally empty: stability guaranteed by refs above

  // Sync effect: only depends on boardState.  handleDeleteItem, setNodes, and
  // setEdges are all stable references — listing them satisfies exhaustive-deps
  // without any loop risk.
  //
  // FIX: Defer edge setting by one animation frame so that ReactFlow has
  // processed the new nodes (measured dimensions, registered IDs) before
  // edges reference them.  Without this delay, edges whose source/target
  // nodes haven't been registered yet are silently dropped by ReactFlow.
  useEffect(() => {
    if (!boardState) return;
    setNodes(toNodes(boardState.items, handleDeleteItem));
    const edgesFromBackend = toEdges(boardState.connections);
    const raf = requestAnimationFrame(() => {
      setEdges(edgesFromBackend);
    });
    return () => cancelAnimationFrame(raf);
  }, [boardState, handleDeleteItem, setNodes, setEdges]);

  // ── Drag → debounced batch save ─────────────────────────────────
  const pendingRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes);
      for (const c of changes) {
        if (c.type === "position" && c.position) {
          pendingRef.current.set(c.id, c.position);
        }
      }
      if (pendingRef.current.size > 0) {
        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
          if (!boardId || pendingRef.current.size === 0) return;
          const items = Array.from(pendingRef.current.entries()).map(
            ([id, pos]) => ({
              id: Number(id),
              position_x: pos.x,
              position_y: pos.y,
            }),
          );
          pendingRef.current.clear();
          batchSaveMut.mutate(items, {
            onError: (err) => {
              setSaveStatus(`Save failed: ${err.message}`);
            },
            onSuccess: () => {
              setSaveStatus("Saved \u2713");
              setTimeout(() => setSaveStatus(""), 2000);
            },
          });
        }, DEBOUNCE_MS);
      }
    },
    [onNodesChange, boardId, batchSaveMut],
  );

  // ── Connect handler (create red line) ───────────────────────────
  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (!boardId || !connection.source || !connection.target) return;
      // Optimistically add edge
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            id: `temp-${Date.now()}`,
          },
          eds,
        ),
      );
      createConnMut.mutate(
        {
          from_item: Number(connection.source),
          to_item: Number(connection.target),
          label: "",
        },
        { onError: () => refetchBoard() },
      );
    },
    [boardId, createConnMut, setEdges, refetchBoard],
  );

  // ── Delete edge ─────────────────────────────────────────────────
  const handleEdgeClick = useCallback(
    (_e: React.MouseEvent, edge: Edge) => {
      const connId = edge.data?.connectionId as number | undefined;
      if (!connId || !boardId) return;
      if (confirm("Delete this connection?")) {
        deleteConnMut.mutate(connId);
      }
    },
    [boardId, deleteConnMut],
  );

  // ── Create note ─────────────────────────────────────────────────
  const handleCreateNote = useCallback(() => {
    if (!boardId || !noteTitle.trim()) return;
    createNoteMut.mutate(
      { title: noteTitle.trim(), content: noteContent.trim() },
      {
        onSuccess: () => {
          setNoteTitle("");
          setNoteContent("");
        },
      },
    );
  }, [boardId, noteTitle, noteContent, createNoteMut]);

  // ── Edit note ───────────────────────────────────────────────────
  const startEditNote = useCallback((note: BoardNote) => {
    setEditingNote(note);
    setEditTitle(note.title);
    setEditContent(note.content);
  }, []);

  const handleSaveNote = useCallback(() => {
    if (!editingNote) return;
    updateNoteMut.mutate(
      {
        noteId: editingNote.id,
        data: { title: editTitle.trim(), content: editContent.trim() },
      },
      { onSuccess: () => setEditingNote(null) },
    );
  }, [editingNote, editTitle, editContent, updateNoteMut]);

  const handleDeleteNote = useCallback(
    (noteId: number) => {
      if (confirm("Delete this note?")) {
        deleteNoteMut.mutate(noteId);
      }
    },
    [deleteNoteMut],
  );

  // ── Pin entity (add item) ──────────────────────────────────────
  const handlePinEntity = useCallback(
    (entity: { content_type_id: number | null; object_id: number }) => {
      createBoardItemMut.mutate(
        {
          content_object: entity,
          position_x: 0,
          position_y: 0,
        },
        { onSuccess: () => setShowPinModal(false) },
      );
    },
    [createBoardItemMut],
  );

  // ── Export PNG ──────────────────────────────────────────────────
  const handleExport = useCallback(async () => {
    if (!reactFlowRef.current) return;
    setExportStatus("Exporting\u2026");
    try {
      const viewport = reactFlowRef.current.querySelector(
        ".react-flow__viewport",
      ) as HTMLElement | null;
      if (!viewport) {
        setExportStatus("Export failed: viewport not found");
        return;
      }
      const dataUrl = await toPng(viewport, {
        backgroundColor: "#f5f0e1",
        quality: 0.95,
      });
      const link = document.createElement("a");
      link.download = `detective-board-case-${caseIdNum}.png`;
      link.href = dataUrl;
      link.click();
      setExportStatus("Exported \u2713");
      setTimeout(() => setExportStatus(""), 3000);
    } catch (err) {
      setExportStatus(
        `Export failed: ${err instanceof Error ? err.message : "unknown"}`,
      );
    }
  }, [caseIdNum]);

  // ── Create board ───────────────────────────────────────────────
  const handleCreateBoard = useCallback(() => {
    if (!caseIdNum) return;
    createBoardMut.mutate(caseIdNum, {
      onSuccess: (board) => setCreatedBoardId(board.id),
    });
  }, [caseIdNum, createBoardMut]);

  // ── Derived state ──────────────────────────────────────────────
  const hasBoard = boardId !== null;
  const isLoading = boardsLoading || boardLoading;
  const error = boardsError || boardError;
  const noBoardForCase =
    !boardsLoading && boards && !boards.find((b) => b.case === caseIdNum);
  const memoNodeTypes = useMemo(() => NODE_TYPES, []);

  // ─────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────
  return (
    <div className={css.page}>
      {/* ── Header ────────────────────────────────────────────── */}
      <div className={css.header}>
        <div>
          <h1 className={css.headerTitle}>
            Detective Board{" "}
            <span className={css.headerSub}>
              {caseIdNum ? `Case #${caseIdNum}` : ""}
            </span>
          </h1>
        </div>
        <div className={css.headerActions}>
          {saveStatus && <span className={css.statusMsg}>{saveStatus}</span>}
          {exportStatus && (
            <span className={css.statusMsg}>{exportStatus}</span>
          )}
          {hasBoard && (
            <>
              <button
                type="button"
                className={css.btn}
                onClick={() => setShowPinModal(true)}
              >
                + Add Item
              </button>
              <button
                type="button"
                className={css.btn}
                onClick={handleExport}
              >
                Export PNG
              </button>
              <button
                type="button"
                className={css.btn}
                onClick={() => refetchBoard()}
              >
                Refresh
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── Error ─────────────────────────────────────────────── */}
      {error && (
        <ErrorState
          message={error instanceof Error ? error.message : String(error)}
          onRetry={() => refetchBoard()}
          compact
        />
      )}

      {/* ── Loading ───────────────────────────────────────────── */}
      {isLoading && (
        <LoadingSpinner label="Loading board data…" />
      )}

      {/* ── No board yet ─────────────────────────────────────── */}
      {!isLoading && noBoardForCase && !hasBoard && (
        <div className={css.centerMsg}>
          <p>No detective board exists for Case #{caseIdNum}.</p>
          <button
            type="button"
            className={css.btnPrimary}
            onClick={handleCreateBoard}
            disabled={createBoardMut.isPending}
          >
            {createBoardMut.isPending
              ? "Creating\u2026"
              : "Create Detective Board"}
          </button>
          {createBoardMut.isError && (
            <p className={css.errorInline}>
              {createBoardMut.error.message}
            </p>
          )}
        </div>
      )}

      {/* ── Board canvas + sidebar ────────────────────────────── */}
      {hasBoard && !isLoading && (
        <div className={css.body}>
          {/* Canvas */}
          <div ref={reactFlowRef} className={css.canvas}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={handleNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onEdgeClick={handleEdgeClick}
              nodeTypes={memoNodeTypes}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              defaultEdgeOptions={DEFAULT_EDGE_OPTS}
              style={{ width: "100%", height: "100%" }}
            >
              <Background
                variant={BackgroundVariant.Dots}
                gap={24}
                size={1}
                color="#c9a96e55"
              />
              <Controls />
              <MiniMap
                nodeColor={() => "#c9a96e"}
                style={{ background: "#faf6eb" }}
              />
            </ReactFlow>
          </div>

          {/* Sidebar */}
          <aside className={css.sidebar}>
            <div className={css.sidebarScroll}>
              {/* Summary */}
              <h3 className={css.sectionTitle}>Board Summary</h3>
              <div className={css.summary}>
                Items: {boardState?.items.length ?? 0} &middot; Connections:{" "}
                {boardState?.connections.length ?? 0} &middot; Notes:{" "}
                {boardState?.notes.length ?? 0}
              </div>

              <hr className={css.divider} />

              {/* Add note */}
              <h3 className={css.sectionTitle}>Add Note</h3>
              <input
                type="text"
                className={css.input}
                placeholder="Note title"
                value={noteTitle}
                onChange={(e) => setNoteTitle(e.target.value)}
              />
              <textarea
                className={css.textarea}
                placeholder="Content (optional)"
                value={noteContent}
                onChange={(e) => setNoteContent(e.target.value)}
                rows={3}
              />
              <button
                type="button"
                className={`${css.btnPrimary} ${css.btnBlock}`}
                onClick={handleCreateNote}
                disabled={!noteTitle.trim() || createNoteMut.isPending}
              >
                {createNoteMut.isPending ? "Creating\u2026" : "Add Note"}
              </button>
              {createNoteMut.isError && (
                <div className={css.errorInline}>
                  {createNoteMut.error.message}
                </div>
              )}

              <hr className={css.divider} />

              {/* Notes list */}
              <h3 className={css.sectionTitle}>Notes</h3>
              {boardState?.notes.length === 0 && (
                <div className={css.emptyHint}>No notes yet.</div>
              )}
              {boardState?.notes.map((n) =>
                editingNote?.id === n.id ? (
                  /* inline edit */
                  <div key={n.id} className={css.noteCard}>
                    <input
                      className={css.input}
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                    />
                    <textarea
                      className={css.textarea}
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      rows={2}
                    />
                    <div className={css.noteActions}>
                      <button
                        type="button"
                        className={css.noteMiniBtn}
                        onClick={handleSaveNote}
                        disabled={updateNoteMut.isPending}
                      >
                        {updateNoteMut.isPending ? "Saving\u2026" : "Save"}
                      </button>
                      <button
                        type="button"
                        className={css.noteMiniBtn}
                        onClick={() => setEditingNote(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div key={n.id} className={css.noteCard}>
                    <div className={css.noteTitle}>{n.title}</div>
                    {n.content && (
                      <div className={css.noteContent}>
                        {n.content.length > 120
                          ? `${n.content.substring(0, 120)}\u2026`
                          : n.content}
                      </div>
                    )}
                    <div className={css.noteActions}>
                      <button
                        type="button"
                        className={css.noteMiniBtn}
                        onClick={() => startEditNote(n)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className={css.noteMiniBtn}
                        onClick={() => handleDeleteNote(n.id)}
                      >
                        Delete
                      </button>
                      {!pinnedNoteIds.has(n.id) && (
                        <button
                          type="button"
                          className={css.noteMiniBtn}
                          onClick={() => handlePinNote(n.id)}
                          disabled={createBoardItemMut.isPending}
                        >
                          {createBoardItemMut.isPending
                            ? "Adding\u2026"
                            : "Add To Board"}
                        </button>
                      )}
                    </div>
                  </div>
                ),
              )}

              <hr className={css.divider} />

              {/* Instructions */}
              <h3 className={css.sectionTitle}>How to Use</h3>
              <ul className={css.instructions}>
                <li>
                  <strong>Drag</strong> items to reposition (auto-saves)
                </li>
                <li>
                  <strong>Connect</strong>: drag from bottom handle to top
                  handle of another item
                </li>
                <li>
                  <strong>Delete connection</strong>: click on a red line
                </li>
                <li>
                  <strong>Remove item</strong>: click X on item card
                </li>
                <li>
                  <strong>Add Item</strong>: pin evidence / suspects from this
                  case
                </li>
                <li>
                  <strong>Export</strong>: download the board as a PNG image
                </li>
              </ul>

              {/* Mutation status */}
              {batchSaveMut.isPending && (
                <div className={css.emptyHint} style={{ marginTop: 8 }}>
                  Saving positions\u2026
                </div>
              )}
            </div>
          </aside>
        </div>
      )}

      {/* Pin entity modal */}
      {showPinModal && boardId && caseIdNum && (
        <PinEntityModal
          caseId={caseIdNum}
          existingItems={boardState?.items ?? []}
          onPin={handlePinEntity}
          isPinning={createBoardItemMut.isPending}
          onClose={() => setShowPinModal(false)}
        />
      )}
    </div>
  );
}
