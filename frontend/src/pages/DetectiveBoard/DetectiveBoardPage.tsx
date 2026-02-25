/**
 * DetectiveBoardPage — Integration spike.
 *
 * Validates the end-to-end data flow:
 *   1. Load board full state from GET /api/board/boards/{id}/full/
 *   2. Render items as draggable React Flow nodes
 *   3. Render connections as red edges
 *   4. Drag-and-drop items → PATCH batch-coordinates
 *   5. Create notes (auto-pinned by backend)
 *   6. Create/delete connections
 *   7. Export canvas as PNG (html-to-image)
 *
 * Route: /detective-board/:caseId
 *
 * NOT production quality — this is a spike to de-risk integration.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import {
  useBoardsList,
  useBoardFull,
  useCreateBoard,
  useCreateNote,
  useCreateConnection,
  useDeleteConnection,
  useDeleteBoardItem,
  useBatchSaveCoordinates,
} from "./useBoardData";
import type {
  BoardItem,
  BoardConnection,
} from "../../types/board";

// ---------------------------------------------------------------------------
// Node type registry
// ---------------------------------------------------------------------------

const nodeTypes = { boardItem: BoardItemNode };

// ---------------------------------------------------------------------------
// Helpers: backend data → React Flow nodes/edges
// ---------------------------------------------------------------------------

function toNodes(
  items: BoardItem[],
  onDelete?: (id: number) => void,
): Node[] {
  return items.map((item) => ({
    id: String(item.id),
    type: "boardItem",
    position: { x: item.position_x, y: item.position_y },
    data: {
      boardItem: item,
      onDelete,
    } satisfies BoardItemNodeData,
  }));
}

function toEdges(connections: BoardConnection[]): Edge[] {
  return connections.map((c) => ({
    id: `conn-${c.id}`,
    source: String(c.from_item),
    target: String(c.to_item),
    label: c.label || undefined,
    type: "default",
    style: { stroke: "#c0392b", strokeWidth: 2 },
    animated: false,
    data: { connectionId: c.id },
  }));
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DetectiveBoardPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const caseIdNum = caseId ? Number(caseId) : null;

  // ── Board discovery ────────────────────────────────────────────
  const {
    data: boards,
    isLoading: boardsLoading,
    error: boardsError,
  } = useBoardsList();

  const [boardId, setBoardId] = useState<number | null>(null);

  // Find or create board for this case
  const createBoardMut = useCreateBoard();

  useEffect(() => {
    if (!boards || !caseIdNum) return;
    const existing = boards.find((b) => b.case === caseIdNum);
    if (existing) {
      setBoardId(existing.id);
    }
    // If no board exists, user can create one via button
  }, [boards, caseIdNum]);

  // ── Full board data ────────────────────────────────────────────
  const {
    data: boardState,
    isLoading: boardLoading,
    error: boardError,
    refetch: refetchBoard,
  } = useBoardFull(boardId);

  // ── React Flow state ──────────────────────────────────────────
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const reactFlowRef = useRef<HTMLDivElement>(null);

  // Mutations (only initialise when boardId is set)
  const createNoteMut = useCreateNote(boardId ?? 0);
  const createConnMut = useCreateConnection(boardId ?? 0);
  const deleteConnMut = useDeleteConnection(boardId ?? 0);
  const deleteItemMut = useDeleteBoardItem(boardId ?? 0);
  const batchSaveMut = useBatchSaveCoordinates(boardId ?? 0);

  // ── Sync backend data → React Flow ────────────────────────────
  const handleDeleteItem = useCallback(
    (itemId: number) => {
      if (!boardId) return;
      if (confirm("Remove this item from the board?")) {
        deleteItemMut.mutate(itemId);
      }
    },
    [boardId, deleteItemMut],
  );

  useEffect(() => {
    if (!boardState) return;
    setNodes(toNodes(boardState.items, handleDeleteItem));
    setEdges(toEdges(boardState.connections));
  }, [boardState, handleDeleteItem, setNodes, setEdges]);

  // ── Drag end → batch save positions ───────────────────────────
  const pendingMovesRef = useRef<Map<string, { x: number; y: number }>>(
    new Map(),
  );
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleNodesChange = useCallback(
    (changes: NodeChange[]) => {
      onNodesChange(changes);

      // Track position changes for batch save
      for (const change of changes) {
        if (change.type === "position" && change.position) {
          pendingMovesRef.current.set(change.id, change.position);
        }
      }

      // Debounced save: 800ms after last drag event
      if (pendingMovesRef.current.size > 0) {
        if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
        saveTimeoutRef.current = setTimeout(() => {
          if (!boardId || pendingMovesRef.current.size === 0) return;
          const items = Array.from(pendingMovesRef.current.entries()).map(
            ([id, pos]) => ({
              id: Number(id),
              position_x: pos.x,
              position_y: pos.y,
            }),
          );
          pendingMovesRef.current.clear();
          batchSaveMut.mutate(items, {
            onError: (err) => {
              console.error("[Board Spike] Batch save failed:", err);
              setSaveStatus(`Save failed: ${err.message}`);
            },
            onSuccess: () => {
              setSaveStatus("Positions saved ✓");
              setTimeout(() => setSaveStatus(""), 2000);
            },
          });
        }, 800);
      }
    },
    [onNodesChange, boardId, batchSaveMut],
  );

  // ── Connect handler (create red line) ─────────────────────────
  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      if (!boardId || !connection.source || !connection.target) return;

      // Optimistically add edge
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            style: { stroke: "#c0392b", strokeWidth: 2 },
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
        {
          onError: (err) => {
            console.error("[Board Spike] Create connection failed:", err);
            // Refetch to revert optimistic update
            refetchBoard();
          },
        },
      );
    },
    [boardId, createConnMut, setEdges, refetchBoard],
  );

  // ── Delete edge handler ───────────────────────────────────────
  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      const connId = edge.data?.connectionId as number | undefined;
      if (!connId || !boardId) return;
      if (confirm("Delete this connection?")) {
        deleteConnMut.mutate(connId);
      }
    },
    [boardId, deleteConnMut],
  );

  // ── Create note ───────────────────────────────────────────────
  const [noteTitle, setNoteTitle] = useState("");
  const [noteContent, setNoteContent] = useState("");

  const handleCreateNote = useCallback(() => {
    if (!boardId || !noteTitle.trim()) return;
    createNoteMut.mutate(
      { title: noteTitle.trim(), content: noteContent.trim() },
      {
        onSuccess: () => {
          setNoteTitle("");
          setNoteContent("");
        },
        onError: (err) => {
          console.error("[Board Spike] Create note failed:", err);
        },
      },
    );
  }, [boardId, noteTitle, noteContent, createNoteMut]);

  // ── Export as PNG ─────────────────────────────────────────────
  const [exportStatus, setExportStatus] = useState("");

  const handleExport = useCallback(async () => {
    if (!reactFlowRef.current) return;
    setExportStatus("Exporting…");
    try {
      // Find the React Flow viewport element
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
      // Trigger download
      const link = document.createElement("a");
      link.download = `detective-board-${boardId}.png`;
      link.href = dataUrl;
      link.click();
      setExportStatus("Exported ✓");
      setTimeout(() => setExportStatus(""), 3000);
    } catch (err) {
      console.error("[Board Spike] Export error:", err);
      setExportStatus(
        `Export failed: ${err instanceof Error ? err.message : "unknown"}`,
      );
    }
  }, [boardId]);

  // ── Handle create board ───────────────────────────────────────
  const handleCreateBoard = useCallback(() => {
    if (!caseIdNum) return;
    createBoardMut.mutate(caseIdNum, {
      onSuccess: (board) => {
        setBoardId(board.id);
      },
      onError: (err) => {
        console.error("[Board Spike] Create board failed:", err);
      },
    });
  }, [caseIdNum, createBoardMut]);

  // ── Status messages ───────────────────────────────────────────
  const [saveStatus, setSaveStatus] = useState("");

  // ── Derive state ──────────────────────────────────────────────
  const hasBoard = boardId !== null;
  const isLoading = boardsLoading || boardLoading;
  const error = boardsError || boardError;
  const noBoardForCase =
    !boardsLoading && boards && !boards.find((b) => b.case === caseIdNum);

  // ── Memoized node types ───────────────────────────────────────
  const memoNodeTypes = useMemo(() => nodeTypes, []);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* ── Header ────────────────────────────────────────────────── */}
      <div
        style={{
          padding: "12px 20px",
          borderBottom: "1px solid #d4c5a9",
          background: "#faf6eb",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: 20,
              fontWeight: 700,
              color: "#3e2723",
            }}
          >
            Detective Board{" "}
            <span style={{ fontWeight: 400, fontSize: 14, color: "#6d4c41" }}>
              {caseIdNum ? `Case #${caseIdNum}` : ""}
              {boardId ? ` · Board #${boardId}` : ""}
            </span>
          </h1>
          <div style={{ fontSize: 11, color: "#8d6e63", marginTop: 2 }}>
            Spike: drag items, connect with red lines, save positions, export
            PNG
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {saveStatus && (
            <span style={{ fontSize: 12, color: "#6d4c41" }}>
              {saveStatus}
            </span>
          )}
          {exportStatus && (
            <span style={{ fontSize: 12, color: "#6d4c41" }}>
              {exportStatus}
            </span>
          )}
          {hasBoard && (
            <>
              <button onClick={handleExport} style={btnStyle}>
                Export PNG
              </button>
              <button
                onClick={() => refetchBoard()}
                style={btnStyle}
              >
                Refresh
              </button>
            </>
          )}
        </div>
      </div>

      {/* ── Error / loading / no board ─────────────────────────── */}
      {error && (
        <div style={{ padding: 16, color: "#c0392b", background: "#fdedec" }}>
          Error: {error instanceof Error ? error.message : String(error)}
        </div>
      )}

      {isLoading && (
        <div style={{ padding: 24, textAlign: "center", color: "#8d6e63" }}>
          Loading board data…
        </div>
      )}

      {!isLoading && noBoardForCase && !hasBoard && (
        <div style={{ padding: 24, textAlign: "center" }}>
          <p style={{ color: "#6d4c41", marginBottom: 12 }}>
            No detective board exists for Case #{caseIdNum}.
          </p>
          <button
            onClick={handleCreateBoard}
            style={{ ...btnStyle, fontSize: 14, padding: "8px 20px" }}
            disabled={createBoardMut.isPending}
          >
            {createBoardMut.isPending
              ? "Creating…"
              : "Create Detective Board"}
          </button>
          {createBoardMut.isError && (
            <p style={{ color: "#c0392b", marginTop: 8, fontSize: 13 }}>
              Failed: {createBoardMut.error.message}
            </p>
          )}
        </div>
      )}

      {/* ── Board canvas + sidebar ────────────────────────────── */}
      {hasBoard && !isLoading && (
        <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
          {/* ── Canvas ────────────────────────────────────────── */}
          <div
            ref={reactFlowRef}
            style={{ flex: 1, background: "#f5f0e1" }}
          >
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
              defaultEdgeOptions={{
                style: { stroke: "#c0392b", strokeWidth: 2 },
              }}
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

          {/* ── Sidebar controls ──────────────────────────────── */}
          <div
            style={{
              width: 260,
              borderLeft: "1px solid #d4c5a9",
              background: "#faf6eb",
              padding: 16,
              overflowY: "auto",
              fontSize: 13,
            }}
          >
            {/* Board summary */}
            <SectionTitle>Board Summary</SectionTitle>
            <div style={{ marginBottom: 12, color: "#6d4c41", fontSize: 12 }}>
              Items: {boardState?.items.length ?? 0} · Connections:{" "}
              {boardState?.connections.length ?? 0} · Notes:{" "}
              {boardState?.notes.length ?? 0}
            </div>

            <hr style={{ border: "none", borderTop: "1px solid #d4c5a9" }} />

            {/* Add note */}
            <SectionTitle>Add Note</SectionTitle>
            <input
              type="text"
              placeholder="Note title"
              value={noteTitle}
              onChange={(e) => setNoteTitle(e.target.value)}
              style={inputStyle}
            />
            <textarea
              placeholder="Content (optional)"
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              rows={3}
              style={{ ...inputStyle, resize: "vertical" }}
            />
            <button
              onClick={handleCreateNote}
              disabled={!noteTitle.trim() || createNoteMut.isPending}
              style={{
                ...btnStyle,
                width: "100%",
                opacity: !noteTitle.trim() ? 0.5 : 1,
              }}
            >
              {createNoteMut.isPending ? "Creating…" : "Add Note"}
            </button>
            {createNoteMut.isError && (
              <div
                style={{ color: "#c0392b", fontSize: 11, marginTop: 4 }}
              >
                {createNoteMut.error.message}
              </div>
            )}

            <hr
              style={{
                border: "none",
                borderTop: "1px solid #d4c5a9",
                margin: "12px 0",
              }}
            />

            {/* Instructions */}
            <SectionTitle>How to Use</SectionTitle>
            <ul
              style={{
                paddingLeft: 16,
                color: "#6d4c41",
                fontSize: 11,
                lineHeight: 1.6,
              }}
            >
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
                <strong>Export</strong>: click "Export PNG" button
              </li>
            </ul>

            <hr
              style={{
                border: "none",
                borderTop: "1px solid #d4c5a9",
                margin: "12px 0",
              }}
            />

            {/* Notes list */}
            <SectionTitle>Notes on Board</SectionTitle>
            {boardState?.notes.length === 0 && (
              <div style={{ color: "#8d6e63", fontSize: 11 }}>
                No notes yet.
              </div>
            )}
            {boardState?.notes.map((n) => (
              <div
                key={n.id}
                style={{
                  background: "#fff",
                  border: "1px solid #e0d6c2",
                  borderRadius: 4,
                  padding: "6px 8px",
                  marginBottom: 6,
                  fontSize: 11,
                }}
              >
                <strong>{n.title}</strong>
                {n.content && (
                  <div style={{ color: "#6d4c41", marginTop: 2 }}>
                    {n.content.substring(0, 100)}
                    {n.content.length > 100 ? "…" : ""}
                  </div>
                )}
              </div>
            ))}

            {/* Mutation status */}
            {batchSaveMut.isPending && (
              <div style={{ color: "#8d6e63", fontSize: 11, marginTop: 8 }}>
                Saving positions…
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tiny reusable bits
// ---------------------------------------------------------------------------

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3
      style={{
        margin: "8px 0 6px",
        fontSize: 13,
        fontWeight: 700,
        color: "#5d4037",
      }}
    >
      {children}
    </h3>
  );
}

const btnStyle: React.CSSProperties = {
  padding: "4px 12px",
  fontSize: 12,
  border: "1px solid #c9a96e",
  borderRadius: 4,
  background: "#faf6eb",
  color: "#5d4037",
  cursor: "pointer",
  fontWeight: 600,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "6px 8px",
  fontSize: 12,
  border: "1px solid #d4c5a9",
  borderRadius: 4,
  marginBottom: 6,
  fontFamily: "inherit",
  boxSizing: "border-box",
};
