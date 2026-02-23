/**
 * Detective Board API service.
 */
import api from './axios.instance';
import type { PaginatedResponse, ListParams } from '@/types/api.types';
import type {
  BoardListItem,
  BoardCreateRequest,
  BoardUpdateRequest,
  FullBoardState,
  BoardItem,
  BoardItemCreateRequest,
  BoardItemBatchCoordinatesRequest,
  BoardNote,
  BoardNoteCreateRequest,
  BoardNoteUpdateRequest,
  BoardConnection,
  BoardConnectionCreateRequest,
} from '@/types/board.types';

export const boardApi = {
  /* ── Board CRUD ─────────────────────────────────────────────────── */
  list: (params?: ListParams) =>
    api
      .get<PaginatedResponse<BoardListItem>>('/boards/', { params })
      .then((r) => r.data),

  detail: (id: number) =>
    api.get<BoardListItem>(`/boards/${id}/`).then((r) => r.data),

  /** Full state = items + connections + notes */
  full: (id: number) =>
    api.get<FullBoardState>(`/boards/${id}/full/`).then((r) => r.data),

  create: (data: BoardCreateRequest) =>
    api.post<BoardListItem>('/boards/', data).then((r) => r.data),

  update: (id: number, data: BoardUpdateRequest) =>
    api.patch<BoardListItem>(`/boards/${id}/`, data).then((r) => r.data),

  delete: (id: number) =>
    api.delete(`/boards/${id}/`).then((r) => r.data),

  /* ── Items ──────────────────────────────────────────────────────── */
  addItem: (boardId: number, data: BoardItemCreateRequest) =>
    api
      .post<BoardItem>(`/boards/${boardId}/items/`, data)
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
      .post<BoardNote>(`/boards/${boardId}/notes/`, data)
      .then((r) => r.data),

  updateNote: (boardId: number, noteId: number, data: BoardNoteUpdateRequest) =>
    api
      .patch<BoardNote>(`/boards/${boardId}/notes/${noteId}/`, data)
      .then((r) => r.data),

  deleteNote: (boardId: number, noteId: number) =>
    api.delete(`/boards/${boardId}/notes/${noteId}/`).then((r) => r.data),

  /* ── Connections ────────────────────────────────────────────────── */
  addConnection: (boardId: number, data: BoardConnectionCreateRequest) =>
    api
      .post<BoardConnection>(`/boards/${boardId}/connections/`, data)
      .then((r) => r.data),

  removeConnection: (boardId: number, connId: number) =>
    api
      .delete(`/boards/${boardId}/connections/${connId}/`)
      .then((r) => r.data),
};
