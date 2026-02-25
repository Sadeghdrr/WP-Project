/**
 * Custom React Flow node for board items.
 *
 * Renders a compact card showing the content object's type and display name.
 * Supports source/target handles for red-line connections.
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { BoardItem } from "../../types/board";

// ---------------------------------------------------------------------------
// Evidence / generic item node
// ---------------------------------------------------------------------------

export interface BoardItemNodeData extends Record<string, unknown> {
  boardItem: BoardItem;
  onDelete?: (itemId: number) => void;
}

function BoardItemNodeInner({ data, selected }: NodeProps) {
  const d = data as unknown as BoardItemNodeData;
  const item = d.boardItem;
  const summary = item.content_object_summary;

  const modelLabel = summary
    ? `${summary.app_label}.${summary.model}`
    : `ct:${item.content_type}`;
  const displayName = summary?.display_name ?? `#${item.object_id}`;

  const iconMap: Record<string, string> = {
    boardnote: "📝",
    case: "📁",
    suspect: "🔍",
    evidence: "🔬",
    testimonyevidence: "💬",
    biologicalevidence: "🧬",
    vehicleevidence: "🚗",
    identityevidence: "🪪",
  };
  const icon = summary ? (iconMap[summary.model] ?? "📌") : "📌";

  return (
    <div
      style={{
        background: selected ? "#fff3cd" : "#fffef5",
        border: selected ? "2px solid #d4a017" : "1px solid #c9a96e",
        borderRadius: 8,
        padding: "8px 12px",
        minWidth: 140,
        maxWidth: 220,
        fontSize: 12,
        fontFamily: "'Courier New', monospace",
        boxShadow: "2px 2px 6px rgba(0,0,0,0.15)",
        cursor: "grab",
        position: "relative",
      }}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: "#c0392b", width: 8, height: 8 }}
      />
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ fontSize: 18 }}>{icon}</span>
        <div>
          <div
            style={{
              fontWeight: 700,
              color: "#5d4037",
              marginBottom: 2,
              wordBreak: "break-word",
            }}
          >
            {displayName}
          </div>
          <div style={{ color: "#8d6e63", fontSize: 10 }}>{modelLabel}</div>
        </div>
      </div>
      {d.onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            d.onDelete!(item.id);
          }}
          title="Remove from board"
          style={{
            position: "absolute",
            top: 2,
            right: 4,
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: 12,
            color: "#c0392b",
            lineHeight: 1,
          }}
        >
          ✕
        </button>
      )}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: "#c0392b", width: 8, height: 8 }}
      />
    </div>
  );
}

export const BoardItemNode = memo(BoardItemNodeInner);
