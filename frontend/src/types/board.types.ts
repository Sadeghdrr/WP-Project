/**
 * Detective Board types — mirrors backend board.models & serializers.
 *
 * Key schemas:
 *  - DetectiveBoardList     → BoardListItem
 *  - FullBoardState         → FullBoardState
 *  - BoardItemInline        → BoardItem
 *  - BoardConnectionInline  → BoardConnection
 *  - BoardNoteInline        → BoardNote
 */

/* ── Board ─────────────────────────────────────────────────────────── */

/** Compact list representation (from DetectiveBoardListSerializer) */
export interface BoardListItem {
  id: number;
  case: number;
  detective: number;
  item_count: number;
  connection_count: number;
  created_at: string;
  updated_at: string;
}

export interface BoardCreateRequest {
  case: number;
}

export type BoardUpdateRequest = Partial<BoardCreateRequest>;

/** Full board graph — single request for the canvas (FullBoardStateSerializer) */
export interface FullBoardState {
  id: number;
  case: number;
  detective: number;
  items: BoardItem[];
  connections: BoardConnection[];
  notes: BoardNote[];
  created_at: string;
  updated_at: string;
}

/* ── Content Object Summary ────────────────────────────────────────── */

/** Resolved GenericForeignKey summary returned by the backend */
export interface ContentObjectSummary {
  content_type_id: number;
  app_label: string;
  model: string;
  object_id: number;
  display_name: string;
  detail_url: string;
}

/* ── Board Item ────────────────────────────────────────────────────── */

/** BoardItemInline from FullBoardState */
export interface BoardItem {
  id: number;
  content_type: number;
  object_id: number;
  content_object_summary: ContentObjectSummary | null;
  position_x: number;
  position_y: number;
  created_at: string;
  updated_at: string;
}

export interface BoardItemCreateRequest {
  content_object: { content_type_id: number; object_id: number };
  position_x?: number;
  position_y?: number;
}

export interface BoardItemBatchCoordinatesRequest {
  items: { id: number; position_x: number; position_y: number }[];
}

/** Response from addItem (BoardItemResponse) */
export interface BoardItemResponse {
  id: number;
  board: number;
  content_type: number;
  object_id: number;
  content_object_summary: ContentObjectSummary | null;
  position_x: number;
  position_y: number;
  created_at: string;
  updated_at: string;
}

/* ── Board Note ────────────────────────────────────────────────────── */

/** BoardNoteInline from FullBoardState */
export interface BoardNote {
  id: number;
  title: string;
  content: string;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface BoardNoteCreateRequest {
  title: string;
  content?: string;
}

export type BoardNoteUpdateRequest = Partial<BoardNoteCreateRequest>;

/** Response from addNote (BoardNoteResponse) */
export interface BoardNoteResponse {
  id: number;
  board: number;
  title: string;
  content: string;
  created_by: number;
  created_at: string;
  updated_at: string;
}

/* ── Connection Draft (UI state for drawing connections) ────────────── */

/** Tracks an in-progress connection draw from one node */
export interface ConnectionDraft {
  fromItemId: number;
}

/* ── Board Connection ──────────────────────────────────────────────── */

/** BoardConnectionInline from FullBoardState */
export interface BoardConnection {
  id: number;
  from_item: number;
  to_item: number;
  label: string;
  created_at: string;
  updated_at: string;
}

export interface BoardConnectionCreateRequest {
  from_item: number;
  to_item: number;
  label?: string;
}

/** Response from addConnection (BoardConnectionResponse) */
export interface BoardConnectionResponse {
  id: number;
  board: number;
  from_item: number;
  to_item: number;
  label: string;
  created_at: string;
  updated_at: string;
}
