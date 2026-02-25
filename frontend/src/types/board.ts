/**
 * Detective Board domain types.
 * Maps to: board app models (DetectiveBoard, BoardNote, BoardItem, BoardConnection).
 */

import type { TimeStamped } from "./common";
import type { UserRef } from "./auth";

// ---------------------------------------------------------------------------
// DetectiveBoard
// ---------------------------------------------------------------------------

export interface DetectiveBoard extends TimeStamped {
  id: number;
  case: number; // OneToOne with Case
  detective: UserRef;
  notes: BoardNote[];
  items: BoardItem[];
  connections: BoardConnection[];
}

// ---------------------------------------------------------------------------
// BoardNote
// ---------------------------------------------------------------------------

export interface BoardNote extends TimeStamped {
  id: number;
  board: number;
  title: string;
  content: string;
  created_by: UserRef;
}

export interface BoardNoteCreateRequest {
  title: string;
  content?: string;
}

// ---------------------------------------------------------------------------
// BoardItem
// ---------------------------------------------------------------------------

export interface BoardItem extends TimeStamped {
  id: number;
  board: number;
  content_type: number; // Django ContentType FK
  object_id: number; // Generic FK target ID
  position_x: number;
  position_y: number;
}

export interface BoardItemCreateRequest {
  content_type: number;
  object_id: number;
  position_x?: number;
  position_y?: number;
}

export interface BoardItemPositionUpdate {
  position_x: number;
  position_y: number;
}

// ---------------------------------------------------------------------------
// BoardConnection
// ---------------------------------------------------------------------------

export interface BoardConnection extends TimeStamped {
  id: number;
  board: number;
  from_item: number; // FK → BoardItem
  to_item: number; // FK → BoardItem
  label: string;
}

export interface BoardConnectionCreateRequest {
  from_item: number;
  to_item: number;
  label?: string;
}
