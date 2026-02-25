/**
 * useBoardData — React Query hook for board data + mutations.
 *
 * Encapsulates all board API interactions for the spike page.
 * Uses @tanstack/react-query for caching, loading/error states,
 * and mutation + invalidation.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getBoardFull,
  listBoards,
  createBoard,
  createBoardNote,
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
  BoardItemPositionUpdate,
} from "../../types/board";

const BOARD_FULL_KEY = "board-full";
const BOARDS_LIST_KEY = "boards-list";

// ---------------------------------------------------------------------------
// List boards
// ---------------------------------------------------------------------------

export function useBoardsList() {
  return useQuery<DetectiveBoardListItem[]>({
    queryKey: [BOARDS_LIST_KEY],
    queryFn: async () => {
      const res = await listBoards();
      if (!res.ok) throw new Error(res.error.message);
      // Backend might return paginated or array — handle both
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
// Create note (auto-pins to board)
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

// ---------------------------------------------------------------------------
// Create connection (red line)
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

// ---------------------------------------------------------------------------
// Delete connection
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Delete board item
// ---------------------------------------------------------------------------

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
    // No invalidation needed — optimistic local positions
  });
}
