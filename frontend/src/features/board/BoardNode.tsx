/**
 * BoardNode — a single draggable node on the detective board.
 *
 * Renders differently based on the node's content type:
 *  - Evidence items show type icon + title
 *  - Suspects show suspect icon + name
 *  - Board notes show sticky-note appearance
 *  - Cases show case icon + title
 *
 * Drag behaviour:
 *  - onMouseDown starts tracking
 *  - onMouseMove updates position (via parent callback)
 *  - onMouseUp finalises the drag and calls onDragEnd
 *
 * Connection drawing:
 *  - Click on the connection handle starts a connection
 *  - When in connection mode, clicking another node completes it
 */
import { useCallback, useRef, useState, memo } from 'react';
import type { BoardItem, ConnectionDraft } from '@/types/board.types';

/** Content type model labels → display config */
const NODE_ICONS: Record<string, { icon: string; color: string }> = {
  evidence: { icon: '🔬', color: '#3b82f6' },
  testimonyevidence: { icon: '📝', color: '#8b5cf6' },
  biologicalevidence: { icon: '🧬', color: '#ef4444' },
  vehicleevidence: { icon: '🚗', color: '#f59e0b' },
  identityevidence: { icon: '🪪', color: '#10b981' },
  suspect: { icon: '🔍', color: '#f97316' },
  case: { icon: '📁', color: '#6366f1' },
  boardnote: { icon: '📌', color: '#eab308' },
};

interface BoardNodeProps {
  item: BoardItem;
  x: number;
  y: number;
  selected: boolean;
  connectionDraft: ConnectionDraft | null;
  onDragEnd: (itemId: number, x: number, y: number) => void;
  onSelect: (itemId: number) => void;
  onStartConnection: (itemId: number) => void;
  onCompleteConnection: (itemId: number) => void;
  onRemove: (itemId: number) => void;
}

export const BoardNode = memo(function BoardNode({
  item,
  x,
  y,
  selected,
  connectionDraft,
  onDragEnd,
  onSelect,
  onStartConnection,
  onCompleteConnection,
  onRemove,
}: BoardNodeProps) {
  const nodeRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0, nodeX: 0, nodeY: 0 });
  const [dragPos, setDragPos] = useState<{ x: number; y: number } | null>(
    null,
  );

  const model = item.content_object_summary?.model ?? 'unknown';
  const config = NODE_ICONS[model] ?? { icon: '📄', color: '#64748b' };
  const displayName =
    item.content_object_summary?.display_name ?? `Item #${item.id}`;

  const isNoteNode = model === 'boardnote';

  // ── Drag handlers ──────────────────────────────────────────────
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return; // left click only
      // Don't start drag on buttons
      if ((e.target as HTMLElement).closest('.board-node__action')) return;

      e.preventDefault();
      e.stopPropagation();
      setDragging(true);
      dragStart.current = { x: e.clientX, y: e.clientY, nodeX: x, nodeY: y };

      const handleMouseMove = (ev: MouseEvent) => {
        const dx = ev.clientX - dragStart.current.x;
        const dy = ev.clientY - dragStart.current.y;
        setDragPos({
          x: dragStart.current.nodeX + dx,
          y: dragStart.current.nodeY + dy,
        });
      };

      const handleMouseUp = (ev: MouseEvent) => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        setDragging(false);

        const dx = ev.clientX - dragStart.current.x;
        const dy = ev.clientY - dragStart.current.y;
        const finalX = dragStart.current.nodeX + dx;
        const finalY = dragStart.current.nodeY + dy;

        setDragPos(null);

        // Only fire onDragEnd if actually moved
        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
          onDragEnd(item.id, finalX, finalY);
        }
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [x, y, item.id, onDragEnd],
  );

  // ── Click handlers ─────────────────────────────────────────────
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (connectionDraft) {
        onCompleteConnection(item.id);
      } else {
        onSelect(item.id);
      }
    },
    [connectionDraft, item.id, onSelect, onCompleteConnection],
  );

  const handleConnectionClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onStartConnection(item.id);
    },
    [item.id, onStartConnection],
  );

  const handleRemoveClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onRemove(item.id);
    },
    [item.id, onRemove],
  );

  const currentX = dragPos?.x ?? x;
  const currentY = dragPos?.y ?? y;

  const classNames = [
    'board-node',
    isNoteNode ? 'board-node--note' : 'board-node--evidence',
    selected ? 'board-node--selected' : '',
    dragging ? 'board-node--dragging' : '',
    connectionDraft ? 'board-node--connectable' : '',
    connectionDraft?.fromItemId === item.id
      ? 'board-node--connection-source'
      : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div
      ref={nodeRef}
      className={classNames}
      style={{
        transform: `translate(${currentX}px, ${currentY}px)`,
        borderColor: config.color,
      }}
      onMouseDown={handleMouseDown}
      onClick={handleClick}
      data-item-id={item.id}
    >
      <div className="board-node__header">
        <span className="board-node__icon">{config.icon}</span>
        <span className="board-node__title">{displayName}</span>
      </div>

      {isNoteNode && (
        <div className="board-node__note-indicator">Sticky Note</div>
      )}

      {!isNoteNode && item.content_object_summary && (
        <div className="board-node__type-label">
          {item.content_object_summary.app_label}
        </div>
      )}

      {/* Action buttons */}
      <div className="board-node__actions">
        <button
          className="board-node__action board-node__action--connect"
          title="Draw connection"
          onClick={handleConnectionClick}
          type="button"
        >
          ↗
        </button>
        <button
          className="board-node__action board-node__action--remove"
          title="Remove from board"
          onClick={handleRemoveClick}
          type="button"
        >
          ✕
        </button>
      </div>
    </div>
  );
});
