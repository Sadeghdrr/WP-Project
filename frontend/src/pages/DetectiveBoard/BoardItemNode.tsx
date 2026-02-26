/**
 * Custom React Flow node for board items.
 *
 * Renders a compact card showing the content object's type and display name.
 * Supports source/target handles for red-line connections.
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { BoardItem } from "../../types/board";
import css from "./BoardItemNode.module.css";

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface BoardItemNodeData extends Record<string, unknown> {
  boardItem: BoardItem;
  onDelete?: (itemId: number) => void;
}

// ---------------------------------------------------------------------------
// Icon lookup by backend model name
// ---------------------------------------------------------------------------

const ICON_MAP: Record<string, string> = {
  boardnote: "📝",
  case: "📁",
  suspect: "🔍",
  evidence: "🔬",
  testimonyevidence: "💬",
  biologicalevidence: "🧬",
  vehicleevidence: "🚗",
  identityevidence: "🪪",
};

const HANDLE_STYLE = { background: "#c0392b", width: 8, height: 8 };

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

function BoardItemNodeInner({ data, selected }: NodeProps) {
  const d = data as unknown as BoardItemNodeData;
  const item = d.boardItem;
  const summary = item.content_object_summary;

  const modelLabel = summary
    ? `${summary.app_label}.${summary.model}`
    : `ct:${item.content_type}`;
  const displayName = summary?.display_name ?? `#${item.object_id}`;
  const icon = summary ? (ICON_MAP[summary.model] ?? "📌") : "📌";

  return (
    <div className={selected ? css.cardSelected : css.card}>
      <Handle type="target" position={Position.Top} style={HANDLE_STYLE} />

      <div className={css.row}>
        <span className={css.icon}>{icon}</span>
        <div>
          <div className={css.name}>{displayName}</div>
          <div className={css.model}>{modelLabel}</div>
        </div>
      </div>

      {d.onDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            d.onDelete!(item.id);
          }}
          className={css.deleteBtn}
          title="Remove from board"
          type="button"
        >
          ✕
        </button>
      )}

      <Handle type="source" position={Position.Bottom} style={HANDLE_STYLE} />
    </div>
  );
}

export const BoardItemNode = memo(BoardItemNodeInner);
