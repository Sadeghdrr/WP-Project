/**
 * KanbanBoardPage — full-screen Detective Board for a specific case.
 *
 * Route: /boards/:id  (id = board PK)
 *
 * Architecture:
 *  - useBoardState hook provides all data + mutations
 *  - BoardToolbar provides actions (add item, note, connect, export, zoom)
 *  - BoardCanvas renders nodes + red-line connections
 *  - BoardAddItemModal lets user pin evidence/suspects
 *  - BoardNoteEditor lets user create/edit sticky notes
 *  - exportBoardImage utility for PNG download
 *
 * Performance:
 *  - Single initial fetch via /boards/{id}/full/
 *  - Debounced batch coordinate save
 *  - React.memo on nodes and edges
 */
import { useState, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useBoardState } from '@/hooks/useBoardState';
import { BoardToolbar } from '@/features/board/BoardToolbar';
import { BoardCanvas } from '@/features/board/BoardCanvas';
import { BoardAddItemModal } from '@/features/board/BoardAddItemModal';
import { BoardNoteEditor } from '@/features/board/BoardNoteEditor';
import { exportBoardImage } from '@/utils/exportBoardImage';
import { Skeleton } from '@/components/ui/Skeleton';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';

const MIN_ZOOM = 0.25;
const MAX_ZOOM = 2;
const ZOOM_STEP = 0.15;

export const KanbanBoardPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const boardId = Number(id);

  const canvasRef = useRef<HTMLDivElement>(null);

  // ── State ──────────────────────────────────────────────────────
  const [showAddModal, setShowAddModal] = useState(false);
  const [showNoteEditor, setShowNoteEditor] = useState(false);
  const [connectionMode, setConnectionMode] = useState(false);
  const [zoom, setZoom] = useState(1);

  // ── Board state from hook ──────────────────────────────────────
  const {
    boardState,
    isLoading,
    error,
    getItemPosition,
    onNodeDragEnd,
    savePending,
    addItem,
    removeItem,
    addingItem,
    addNote,
    addingNote,
    deleteNote,
    connectionDraft,
    startConnection,
    completeConnection,
    cancelConnection,
    removeConnection,
  } = useBoardState(boardId);

  // ── Zoom controls ──────────────────────────────────────────────
  const handleZoomIn = useCallback(() => {
    setZoom((z) => Math.min(z + ZOOM_STEP, MAX_ZOOM));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((z) => Math.max(z - ZOOM_STEP, MIN_ZOOM));
  }, []);

  const handleZoomReset = useCallback(() => {
    setZoom(1);
  }, []);

  // ── Connection mode toggle ─────────────────────────────────────
  const handleToggleConnectionMode = useCallback(() => {
    setConnectionMode(true);
  }, []);

  const handleCancelConnection = useCallback(() => {
    setConnectionMode(false);
    cancelConnection();
  }, [cancelConnection]);

  // ── Export ──────────────────────────────────────────────────────
  const handleExport = useCallback(async () => {
    if (!canvasRef.current) return;
    try {
      await exportBoardImage(
        canvasRef.current,
        `detective-board-${boardId}.png`,
      );
    } catch (err) {
      console.error('Board export failed:', err);
    }
  }, [boardId]);

  // ── Note create ────────────────────────────────────────────────
  const handleNoteSave = useCallback(
    (title: string, content: string) => {
      addNote({ title, content: content || undefined });
      setShowNoteEditor(false);
    },
    [addNote],
  );

  // ── Early returns ──────────────────────────────────────────────
  if (isNaN(boardId)) {
    return (
      <div className="board-page board-page--error">
        <Alert type="error" title="Invalid Board">
          The board ID in the URL is not valid.
        </Alert>
        <Button variant="secondary" onClick={() => navigate(-1)}>
          Go Back
        </Button>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="board-page board-page--loading">
        <Skeleton variant="rectangular" width="100%" height={48} />
        <Skeleton variant="rectangular" width="100%" height="80vh" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="board-page board-page--error">
        <Alert type="error" title="Failed to load board">
          Could not fetch the detective board. Please try again.
        </Alert>
        <Button variant="secondary" onClick={() => navigate(-1)}>
          Go Back
        </Button>
      </div>
    );
  }

  const caseId = boardState?.case ?? 0;
  const items = boardState?.items ?? [];
  const connections = boardState?.connections ?? [];

  return (
    <div className="board-page">
      <BoardToolbar
        boardId={boardId}
        caseId={caseId}
        savePending={savePending}
        connectionMode={connectionMode || connectionDraft !== null}
        onAddItemClick={() => setShowAddModal(true)}
        onAddNoteClick={() => setShowNoteEditor(true)}
        onToggleConnectionMode={handleToggleConnectionMode}
        onCancelConnection={handleCancelConnection}
        onExport={handleExport}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onZoomReset={handleZoomReset}
        zoom={zoom}
      />

      <BoardCanvas
        ref={canvasRef}
        items={items}
        connections={connections}
        connectionDraft={connectionDraft}
        zoom={zoom}
        getItemPosition={getItemPosition}
        onNodeDragEnd={onNodeDragEnd}
        onStartConnection={startConnection}
        onCompleteConnection={completeConnection}
        onCancelConnection={handleCancelConnection}
        onRemoveConnection={removeConnection}
        onRemoveItem={removeItem}
      />

      {/* Pin item modal */}
      <BoardAddItemModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        caseId={caseId}
        existingItems={items}
        onAddItem={(data) => {
          addItem(data);
          setShowAddModal(false);
        }}
        adding={addingItem}
      />

      {/* Note editor */}
      <BoardNoteEditor
        open={showNoteEditor}
        onClose={() => setShowNoteEditor(false)}
        onSave={handleNoteSave}
        onDelete={deleteNote}
        saving={addingNote}
      />
    </div>
  );
};
