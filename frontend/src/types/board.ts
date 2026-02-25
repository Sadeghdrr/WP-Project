/**
 * Detective Board domain types.
 * Maps to: board app models (DetectiveBoard, BoardNote, BoardItem, BoardConnection).
 *
 * Payload shapes verified against backend/board/serializers.py
 * (FullBoardStateSerializer, BoardItemResponseSerializer, etc.)
 */

import type { TimeStamped } from "./common";

// ---------------------------------------------------------------------------
// DetectiveBoard (list response — DetectiveBoardListSerializer)
// ---------------------------------------------------------------------------

export interface DetectiveBoardListItem extends TimeStamped {
  id: number;
  case: number;
  detective: number;
  item_count: number;
  connection_count: number;
}

// ---------------------------------------------------------------------------
// GenericForeignKey summary (GenericObjectRelatedField.to_representation)
// ---------------------------------------------------------------------------

export interface ContentObjectSummary {
  content_type_id: number;
  app_label: string;
  model: string;
  object_id: number;
  display_name: string;
  detail_url: string;
}

// ---------------------------------------------------------------------------
// BoardItem (BoardItemInlineSerializer / BoardItemResponseSerializer)
// ---------------------------------------------------------------------------

export interface BoardItem extends TimeStamped {
  id: number;
  content_type: number;
  object_id: number;
  content_object_summary: ContentObjectSummary | null;
  position_x: number;
  position_y: number;
}

export interface BoardItemWithBoard extends BoardItem {
  board: number;
}

export interface BoardItemCreateRequest {
  content_object: {
    content_type_id: number;
    object_id: number;
  };
  position_x?: number;
  position_y?: number;
}

export interface BoardItemPositionUpdate {
  id: number;
  position_x: number;
  position_y: number;
}

// ---------------------------------------------------------------------------
// BoardNote (BoardNoteInlineSerializer / BoardNoteResponseSerializer)
// ---------------------------------------------------------------------------

export interface BoardNote extends TimeStamped {
  id: number;
  title: string;
  content: string;
  created_by: number;
}

export interface BoardNoteWithBoard extends BoardNote {
  board: number;
}

export interface BoardNoteCreateRequest {
  title: string;
  content?: string;
}

// ---------------------------------------------------------------------------
// BoardConnection (BoardConnectionInlineSerializer / BoardConnectionResponseSerializer)
// ---------------------------------------------------------------------------

export interface BoardConnection extends TimeStamped {
  id: number;
  from_item: number;
  to_item: number;
  label: string;
}

export interface BoardConnectionWithBoard extends BoardConnection {
  board: number;
}

export interface BoardConnectionCreateRequest {
  from_item: number;
  to_item: number;
  label?: string;
}

// ---------------------------------------------------------------------------
// FullBoardState (FullBoardStateSerializer) — the main read payload
// ---------------------------------------------------------------------------

export interface FullBoardState extends TimeStamped {
  id: number;
  case: number;
  detective: number;
  items: BoardItem[];
  connections: BoardConnection[];
  notes: BoardNote[];
}

// ---------------------------------------------------------------------------
// Batch coordinate update payload (BatchCoordinateUpdateSerializer)
// ---------------------------------------------------------------------------

export interface BatchCoordinateUpdateRequest {
  items: BoardItemPositionUpdate[];
}
