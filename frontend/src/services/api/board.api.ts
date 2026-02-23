/**
 * Detective Board API service.
 *
 * Endpoints:
 *  - Board CRUD:  GET/POST /boards/, GET/PATCH/DELETE /boards/{id}/
 *  - Full state:  GET /boards/{id}/full/
 *  - Items:       POST /boards/{board_pk}/items/, DELETE .../{id}/
 *  - Batch move:  PATCH /boards/{board_pk}/items/batch-coordinates/
 *  - Notes:       POST/GET/PATCH/DELETE /boards/{board_pk}/notes/...
 *  - Connections: POST/DELETE /boards/{board_pk}/connections/...
 */
import api from './axios.instance';
import type {
  BoardListItem,
  BoardCreateRequest,
  BoardUpdateRequest,
  FullBoardState,
  BoardItemResponse,
  BoardItemCreateRequest,
  BoardItemBatchCoordinatesRequest,
  BoardNoteResponse,
  BoardNoteCreateRequest,
  BoardNoteUpdateRequest,
  BoardConnectionResponse,
  BoardConnectionCreateRequest,
} from '@/types/board.types';

export const boardApi = {
  /* ── Board CRUD ─────────────────────────────────────────────────── */
  list: () =>
    api.get<BoardListItem[]>('/boards/').then((r) => r.data),

  detail: (id: number) =>
    api.get<BoardListItem>(`/boards/${id}/`).then((r) => r.data),

  /** Full state = items + connections + notes in one request */
  full: (id: number) =>
    api.get<FullBoardState>(`/boards/${id}/full/`).then((r) => r.data),

  create: (data: BoardCreateRequest) =>
    api.post<BoardListItem>('/boards/', data).then((r) => r.data),

  update: (id: number, data: BoardUpdateRequest) =>
    api.patch<BoardListItem>(`/boards/${id}/`, data).then((r) => r.data),

  delete: (id: number) => api.delete(`/boards/${id}/`).then((r) => r.data),

  /* ── Items ──────────────────────────────────────────────────────── */
  addItem: (boardId: number, data: BoardItemCreateRequest) =>
    api
      .post<BoardItemResponse>(`/boards/${boardId}/items/`, data)
      .then((r) => r.data),

  removeItem: (boardId: number, itemId: number) =>
    api.delete(`/boards/${boardId}/items/${itemId}/`).then((r) => r.data),

  batchUpdateCoordinates: (
    boardId: number,
    data: BoardItemBatchCoordinatesRequest,
  ) =>
    api
      .patch(`/boards/${boardId}/items/batch-coordinates/`, data)
      .then((r) => r.data),

  /* ── Notes ──────────────────────────────────────────────────────── */
  addNote: (boardId: number, data: BoardNoteCreateRequest) =>
    api
      .post<BoardNoteResponse>(`/boards/${boardId}/notes/`, data)
      .then((r) => r.data),

  getNote: (boardId: number, noteId: number) =>
    api
      .get<BoardNoteResponse>(`/boards/${boardId}/notes/${noteId}/`)
      .then((r) => r.data),

  updateNote: (
    boardId: number,
    noteId: number,
    data: BoardNoteUpdateRequest,
  ) =>
    api
      .patch<BoardNoteResponse>(`/boards/${boardId}/notes/${noteId}/`, data)
      .then((r) => r.data),

  deleteNote: (boardId: number, noteId: number) =>
    api.delete(`/boards/${boardId}/notes/${noteId}/`).then((r) => r.data),

  /* ── Connections ────────────────────────────────────────────────── */
  addConnection: (boardId: number, data: BoardConnectionCreateRequest) =>
    api
      .post<BoardConnectionResponse>(
        `/boards/${boardId}/connections/`,
        data,
      )
      .then((r) => r.data),

  removeConnection: (boardId: number, connId: number) =>
    api
      .delete(`/boards/${boardId}/connections/${connId}/`)
      .then((r) => r.data),
};
