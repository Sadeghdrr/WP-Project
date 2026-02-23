/**
 * Detective Board types — mirrors backend board.models.
 */
import type { UserListItem } from './user.types';

/* ── Board ─────────────────────────────────────────────────────────── */

export interface BoardListItem {
  id: number;
  case: number;
  title: string;
  created_by: UserListItem;
  created_at: string;
  updated_at: string;
}

export interface BoardCreateRequest {
  case: number;
  title: string;
}

export type BoardUpdateRequest = Partial<BoardCreateRequest>;

/** Full board state including items, notes, and connections */
export interface FullBoardState extends BoardListItem {
  items: BoardItem[];
  connections: BoardConnection[];
  notes: BoardNote[];
}

/* ── Board Item ────────────────────────────────────────────────────── */

export interface BoardItem {
  id: number;
  content_type: string;
  object_id: number;
  content_object_summary: string;
  position_x: number;
  position_y: number;
}

export interface BoardItemCreateRequest {
  content_object: string;
  position_x: number;
  position_y: number;
}

export interface BoardItemBatchCoordinatesRequest {
  items: { id: number; position_x: number; position_y: number }[];
}

/* ── Board Note ────────────────────────────────────────────────────── */

export interface BoardNote {
  id: number;
  title: string;
  content: string;
  created_by: UserListItem;
  created_at: string;
}

export interface BoardNoteCreateRequest {
  title: string;
  content: string;
}

export type BoardNoteUpdateRequest = Partial<BoardNoteCreateRequest>;

/* ── Board Connection ──────────────────────────────────────────────── */

export interface BoardConnection {
  id: number;
  from_item: number;
  to_item: number;
  label: string;
}

export interface BoardConnectionCreateRequest {
  from_item: number;
  to_item: number;
  label?: string;
}
