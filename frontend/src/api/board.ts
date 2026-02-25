/**
 * Board API functions.
 *
 * Maps to backend/board/ endpoints for the Detective Board spike.
 * All functions use the centralised apiFetch wrapper for auth + error handling.
 */

import { apiGet, apiPost, apiPatch, apiDelete } from "./client";
import { API } from "./endpoints";
import type { ApiResponse } from "./client";
import type {
  FullBoardState,
  DetectiveBoardListItem,
  BoardItemWithBoard,
  BoardItemCreateRequest,
  BatchCoordinateUpdateRequest,
  BoardConnectionWithBoard,
  BoardConnectionCreateRequest,
  BoardNoteWithBoard,
  BoardNoteCreateRequest,
} from "../types/board";

// ---------------------------------------------------------------------------
// Board CRUD
// ---------------------------------------------------------------------------

/** List all boards visible to the current user. */
export function listBoards(): Promise<ApiResponse<DetectiveBoardListItem[]>> {
  return apiGet<DetectiveBoardListItem[]>(API.BOARDS);
}

/** Get full board graph (items + connections + notes) in one call. */
export function getBoardFull(
  boardId: number,
): Promise<ApiResponse<FullBoardState>> {
  return apiGet<FullBoardState>(API.boardFull(boardId));
}

/** Create a new board for a case. */
export function createBoard(
  caseId: number,
): Promise<ApiResponse<DetectiveBoardListItem>> {
  return apiPost<DetectiveBoardListItem>(API.BOARDS, { case: caseId });
}

/** Delete a board. */
export function deleteBoard(boardId: number): Promise<ApiResponse<void>> {
  return apiDelete(API.board(boardId));
}

// ---------------------------------------------------------------------------
// Board Items (pins)
// ---------------------------------------------------------------------------

/** Pin a content object to the board. */
export function createBoardItem(
  boardId: number,
  data: BoardItemCreateRequest,
): Promise<ApiResponse<BoardItemWithBoard>> {
  return apiPost<BoardItemWithBoard>(API.boardItems(boardId), data);
}

/** Remove a pin from the board. */
export function deleteBoardItem(
  boardId: number,
  itemId: number,
): Promise<ApiResponse<void>> {
  return apiDelete(API.boardItem(boardId, itemId));
}

/** Batch update item coordinates (drag-and-drop save). */
export function batchUpdateCoordinates(
  boardId: number,
  data: BatchCoordinateUpdateRequest,
): Promise<ApiResponse<BoardItemWithBoard[]>> {
  return apiPatch<BoardItemWithBoard[]>(
    API.boardItemsBatchCoordinates(boardId),
    data,
  );
}

// ---------------------------------------------------------------------------
// Board Connections (red lines)
// ---------------------------------------------------------------------------

/** Create a red-line connection between two board items. */
export function createBoardConnection(
  boardId: number,
  data: BoardConnectionCreateRequest,
): Promise<ApiResponse<BoardConnectionWithBoard>> {
  return apiPost<BoardConnectionWithBoard>(
    API.boardConnections(boardId),
    data,
  );
}

/** Delete a connection. */
export function deleteBoardConnection(
  boardId: number,
  connId: number,
): Promise<ApiResponse<void>> {
  return apiDelete(API.boardConnection(boardId, connId));
}

// ---------------------------------------------------------------------------
// Board Notes (sticky notes)
// ---------------------------------------------------------------------------

/** Create a sticky note on the board. */
export function createBoardNote(
  boardId: number,
  data: BoardNoteCreateRequest,
): Promise<ApiResponse<BoardNoteWithBoard>> {
  return apiPost<BoardNoteWithBoard>(API.boardNotes(boardId), data);
}

/** Update a sticky note. */
export function updateBoardNote(
  boardId: number,
  noteId: number,
  data: Partial<BoardNoteCreateRequest>,
): Promise<ApiResponse<BoardNoteWithBoard>> {
  return apiPatch<BoardNoteWithBoard>(API.boardNote(boardId, noteId), data);
}

/** Delete a sticky note. */
export function deleteBoardNote(
  boardId: number,
  noteId: number,
): Promise<ApiResponse<void>> {
  return apiDelete(API.boardNote(boardId, noteId));
}
