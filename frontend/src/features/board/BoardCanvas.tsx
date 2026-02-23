/**
 * BoardCanvas — main interactive canvas for the Detective Board.
 *
 * This component composes:
 *  - BoardEdges (SVG red-line connection layer)
 *  - BoardNode instances (draggable DOM elements)
 *
 * Handles:
 *  - Canvas click to deselect / cancel connection
 *  - Keyboard: Escape to cancel connection
 *  - Pan with middle-mouse or Shift+drag
 *  - Zoom transform is applied from parent
 *
 * The canvas uses CSS transform for zoom and exposes a ref for image export.
 */
import { useCallback, useEffect, useRef, useState, forwardRef } from 'react';
import { BoardEdges } from './BoardEdges';
import { BoardNode } from './BoardNode';
import type {
  BoardItem,
  BoardConnection,
  ConnectionDraft,
} from '@/types/board.types';

interface BoardCanvasProps {
  items: BoardItem[];
  connections: BoardConnection[];
  connectionDraft: ConnectionDraft | null;
  zoom: number;
  getItemPosition: (item: BoardItem) => { x: number; y: number };
  onNodeDragEnd: (itemId: number, x: number, y: number) => void;
  onStartConnection: (itemId: number) => void;
  onCompleteConnection: (itemId: number) => void;
  onCancelConnection: () => void;
  onRemoveConnection: (connId: number) => void;
  onRemoveItem: (itemId: number) => void;
}

export const BoardCanvas = forwardRef<HTMLDivElement, BoardCanvasProps>(
  function BoardCanvas(
    {
      items,
      connections,
      connectionDraft,
      zoom,
      getItemPosition,
      onNodeDragEnd,
      onStartConnection,
      onCompleteConnection,
      onCancelConnection,
      onRemoveConnection,
      onRemoveItem,
    },
    ref,
  ) {
    const [selectedItemId, setSelectedItemId] = useState<number | null>(null);

    // ── Pan state ──────────────────────────────────────────────────
    const [pan, setPan] = useState({ x: 0, y: 0 });
    const panRef = useRef({ active: false, startX: 0, startY: 0, panX: 0, panY: 0 });

    // ── Keyboard handler ───────────────────────────────────────────
    useEffect(() => {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Escape') {
          onCancelConnection();
          setSelectedItemId(null);
        }
      };
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onCancelConnection]);

    // ── Canvas click → deselect ────────────────────────────────────
    const handleCanvasClick = useCallback(() => {
      if (connectionDraft) {
        onCancelConnection();
      }
      setSelectedItemId(null);
    }, [connectionDraft, onCancelConnection]);

    // ── Middle-mouse / Shift-drag panning ──────────────────────────
    const handleCanvasMouseDown = useCallback(
      (e: React.MouseEvent) => {
        // Middle button or Shift+Left
        if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
          e.preventDefault();
          panRef.current = {
            active: true,
            startX: e.clientX,
            startY: e.clientY,
            panX: pan.x,
            panY: pan.y,
          };

          const handleMouseMove = (ev: MouseEvent) => {
            if (!panRef.current.active) return;
            setPan({
              x: panRef.current.panX + (ev.clientX - panRef.current.startX),
              y: panRef.current.panY + (ev.clientY - panRef.current.startY),
            });
          };

          const handleMouseUp = () => {
            panRef.current.active = false;
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
          };

          document.addEventListener('mousemove', handleMouseMove);
          document.addEventListener('mouseup', handleMouseUp);
        }
      },
      [pan],
    );

    const handleSelect = useCallback((itemId: number) => {
      setSelectedItemId(itemId);
    }, []);

    return (
      <div
        className="board-canvas"
        onClick={handleCanvasClick}
        onMouseDown={handleCanvasMouseDown}
      >
        <div
          ref={ref}
          className="board-canvas__inner"
          style={{
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            transformOrigin: '0 0',
          }}
        >
          {/* SVG red-line connections */}
          <BoardEdges
            connections={connections}
            items={items}
            getPosition={getItemPosition}
            onRemoveConnection={onRemoveConnection}
          />

          {/* Draggable nodes */}
          {items.map((item) => {
            const pos = getItemPosition(item);
            return (
              <BoardNode
                key={item.id}
                item={item}
                x={pos.x}
                y={pos.y}
                selected={selectedItemId === item.id}
                connectionDraft={connectionDraft}
                onDragEnd={onNodeDragEnd}
                onSelect={handleSelect}
                onStartConnection={onStartConnection}
                onCompleteConnection={onCompleteConnection}
                onRemove={onRemoveItem}
              />
            );
          })}

          {/* Empty state */}
          {items.length === 0 && (
            <div className="board-canvas__empty">
              <p>Board is empty. Pin evidence or add notes to get started.</p>
            </div>
          )}
        </div>
      </div>
    );
  },
);
