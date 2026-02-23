/**
 * BoardEdges — SVG layer that draws red-line connections between board nodes.
 *
 * Each connection is rendered as an SVG <line> between the center points
 * of the connected items. The SVG overlay is absolutely positioned over
 * the board canvas and is pointer-events: none (except on the lines
 * themselves, which can be clicked to delete).
 *
 * Performance: This component only re-renders when connections or
 * item positions change. Lines are drawn using simple SVG for clarity.
 */
import { useCallback, memo } from 'react';
import type { BoardItem, BoardConnection } from '@/types/board.types';

/** Node dimensions for center-point calculation */
const NODE_WIDTH = 180;
const NODE_HEIGHT = 80;

interface BoardEdgesProps {
  connections: BoardConnection[];
  items: BoardItem[];
  getPosition: (item: BoardItem) => { x: number; y: number };
  onRemoveConnection: (connId: number) => void;
}

export const BoardEdges = memo(function BoardEdges({
  connections,
  items,
  getPosition,
  onRemoveConnection,
}: BoardEdgesProps) {
  const itemMap = new Map(items.map((it) => [it.id, it]));

  const handleLineClick = useCallback(
    (e: React.MouseEvent, connId: number) => {
      e.stopPropagation();
      onRemoveConnection(connId);
    },
    [onRemoveConnection],
  );

  return (
    <svg className="board-edges" aria-hidden="true">
      <defs>
        <marker
          id="arrowhead"
          markerWidth="8"
          markerHeight="6"
          refX="8"
          refY="3"
          orient="auto"
        >
          <polygon points="0 0, 8 3, 0 6" fill="#dc2626" />
        </marker>
      </defs>
      {connections.map((conn) => {
        const fromItem = itemMap.get(conn.from_item);
        const toItem = itemMap.get(conn.to_item);
        if (!fromItem || !toItem) return null;

        const fromPos = getPosition(fromItem);
        const toPos = getPosition(toItem);

        const x1 = fromPos.x + NODE_WIDTH / 2;
        const y1 = fromPos.y + NODE_HEIGHT / 2;
        const x2 = toPos.x + NODE_WIDTH / 2;
        const y2 = toPos.y + NODE_HEIGHT / 2;

        // Label midpoint
        const mx = (x1 + x2) / 2;
        const my = (y1 + y2) / 2;

        return (
          <g key={conn.id} className="board-edge">
            {/* Invisible wider line for easier clicking */}
            <line
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="transparent"
              strokeWidth={12}
              style={{ cursor: 'pointer', pointerEvents: 'stroke' }}
              onClick={(e) => handleLineClick(e, conn.id)}
            />
            {/* Visible red line */}
            <line
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="#dc2626"
              strokeWidth={2.5}
              strokeLinecap="round"
              markerEnd="url(#arrowhead)"
              style={{ pointerEvents: 'none' }}
            />
            {/* Optional label */}
            {conn.label && (
              <text
                x={mx}
                y={my - 6}
                className="board-edge__label"
                textAnchor="middle"
              >
                {conn.label}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
});
