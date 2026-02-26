/**
 * useBoardData — React Query hooks for Detective Board.
 *
 * Encapsulates all board API interactions: list, full graph, mutations for
 * items, connections, and notes. Uses @tanstack/react-query for caching,
 * loading/error states, and mutation + invalidation.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getBoardFull,
  listBoards,
  createBoard,
  deleteBoard,
  createBoardItem,
  createBoardNote,
  updateBoardNote,
  deleteBoardNote,
  createBoardConnection,
  deleteBoardConnection,
  deleteBoardItem,
  batchUpdateCoordinates,
} from "../../api/board";
import type {
  FullBoardState,
  DetectiveBoardListItem,
  BoardNoteCreateRequest,
  BoardConnectionCreateRequest,
  BoardItemCreateRequest,
  BoardItemPositionUpdate,
} from "../../types/board";

export const BOARD_FULL_KEY = "board-full";
export const BOARDS_LIST_KEY = "boards-list";

// ---------------------------------------------------------------------------
// List boards
// ---------------------------------------------------------------------------

export function useBoardsList() {
  return useQuery<DetectiveBoardListItem[]>({
    queryKey: [BOARDS_LIST_KEY],
    queryFn: async () => {
      const res = await listBoards();
      if (!res.ok) throw new Error(res.error.message);
      const data = res.data as unknown;
      if (Array.isArray(data)) return data;
      if (data && typeof data === "object" && "results" in data) {
        return (data as { results: DetectiveBoardListItem[] }).results;
      }
      return [];
    },
  });
}

// ---------------------------------------------------------------------------
// Board for a specific case (derived from list)
// ---------------------------------------------------------------------------

/**
 * Returns the board belonging to a specific case.
 * Reuses useBoardsList and filters client-side.
 * Backend enforces at most one board per case.
 */
export function useBoardForCase(caseId: number | undefined) {
  const { data: boards, isLoading, error, refetch } = useBoardsList();
  const board = boards?.find((b) => b.case === caseId) ?? null;
  return { board, boards, isLoading, error, refetch };
}

// ---------------------------------------------------------------------------
// Delete board
// ---------------------------------------------------------------------------

export function useDeleteBoard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (boardId: number) => {
      const res = await deleteBoard(boardId);
      if (!res.ok) throw new Error(res.error.message);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [BOARDS_LIST_KEY] });
    },
  });
}

// ---------------------------------------------------------------------------
// Full board state
// ---------------------------------------------------------------------------

export function useBoardFull(boardId: number | null) {
  return useQuery<FullBoardState>({
    queryKey: [BOARD_FULL_KEY, boardId],
    queryFn: async () => {
      if (!boardId) throw new Error("No board ID");
      const res = await getBoardFull(boardId);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    enabled: !!boardId,
  });
}

// ---------------------------------------------------------------------------
// Create board for case
// ---------------------------------------------------------------------------

export function useCreateBoard() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (caseId: number) => {
      const res = await createBoard(caseId);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [BOARDS_LIST_KEY] });
    },
  });
}

// ---------------------------------------------------------------------------
// Board Items (pins)
// ---------------------------------------------------------------------------

export function useCreateBoardItem(boardId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: BoardItemCreateRequest) => {
      const res = await createBoardItem(boardId, data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [BOARD_FULL_KEY, boardId] });
    },
  });
}

export function useDeleteBoardItem(boardId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (itemId: number) => {
      const res = await deleteBoardItem(boardId, itemId);
      if (!res.ok) throw new Error(res.error.message);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [BOARD_FULL_KEY, boardId] });
    },
  });
}

// ---------------------------------------------------------------------------
// Batch save coordinates (drag-and-drop)
// ---------------------------------------------------------------------------

export function useBatchSaveCoordinates(boardId: number) {
  return useMutation({
    mutationFn: async (items: BoardItemPositionUpdate[]) => {
      const res = await batchUpdateCoordinates(boardId, { items });
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    // No invalidation needed — optimistic local positions are already correct
  });
}

// ---------------------------------------------------------------------------
// Notes
// ---------------------------------------------------------------------------

export function useCreateNote(boardId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: BoardNoteCreateRequest) => {
      const res = await createBoardNote(boardId, data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [BOARD_FULL_KEY, boardId] });
    },
  });
}

export function useUpdateNote(boardId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      noteId,
      data,
    }: {
      noteId: number;
      data: Partial<BoardNoteCreateRequest>;
    }) => {
      const res = await updateBoardNote(boardId, noteId, data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [BOARD_FULL_KEY, boardId] });
    },
  });
}

export function useDeleteNote(boardId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (noteId: number) => {
      const res = await deleteBoardNote(boardId, noteId);
      if (!res.ok) throw new Error(res.error.message);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [BOARD_FULL_KEY, boardId] });
    },
  });
}

// ---------------------------------------------------------------------------
// Connections (red lines)
// ---------------------------------------------------------------------------

export function useCreateConnection(boardId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: BoardConnectionCreateRequest) => {
      const res = await createBoardConnection(boardId, data);
      if (!res.ok) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [BOARD_FULL_KEY, boardId] });
    },
  });
}

export function useDeleteConnection(boardId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (connId: number) => {
      const res = await deleteBoardConnection(boardId, connId);
      if (!res.ok) throw new Error(res.error.message);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [BOARD_FULL_KEY, boardId] });
    },
  });
}
