/**
 * useBoardState — state management hook for the Detective Board.
 *
 * Architecture layers:
 *  1. React Query fetches the full board graph (items + connections + notes)
 *     via a single GET /boards/{id}/full/ call.
 *  2. Local state tracks in-flight drag positions so the UI updates instantly.
 *  3. Mutations (add/remove item, add/remove connection, notes CRUD) use
 *     optimistic updates + React Query cache invalidation.
 *  4. Batch coordinate save is debounced to avoid excessive API calls on drag.
 *
 * Performance:
 *  - The full board state is fetched once on mount (staleTime: 60s).
 *  - Drag positions are tracked locally and flushed in a single batch PATCH.
 *  - Each mutation only invalidates the 'board-full' query key.
 */
import { useCallback, useRef, useState } from 'react';
import {
  useQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query';
import { boardApi } from '@/services/api/board.api';
import type {
  FullBoardState,
  BoardItem,
  BoardItemCreateRequest,
  BoardNoteCreateRequest,
  BoardNoteUpdateRequest,
  BoardConnectionCreateRequest,
  ConnectionDraft,
} from '@/types/board.types';

/** Debounce delay for batch coordinate saves (ms) */
const BATCH_SAVE_DELAY = 800;

/** React Query staleTime for the board graph */
const BOARD_STALE_TIME = 60_000;

export interface UseBoardStateReturn {
  /* ── Data ─────────────────────────────────────────────────────── */
  boardState: FullBoardState | undefined;
  isLoading: boolean;
  error: unknown;

  /** Local position overrides — merged on top of server positions */
  localPositions: Record<number, { x: number; y: number }>;

  /** Get effective position for an item (local override or server) */
  getItemPosition: (item: BoardItem) => { x: number; y: number };

  /* ── Drag & Drop ─────────────────────────────────────────────── */
  onNodeDragEnd: (itemId: number, x: number, y: number) => void;
  savePending: boolean;

  /* ── Items ────────────────────────────────────────────────────── */
  addItem: (data: BoardItemCreateRequest) => void;
  removeItem: (itemId: number) => void;
  addingItem: boolean;

  /* ── Notes ────────────────────────────────────────────────────── */
  addNote: (data: BoardNoteCreateRequest) => void;
  updateNote: (noteId: number, data: BoardNoteUpdateRequest) => void;
  deleteNote: (noteId: number) => void;
  addingNote: boolean;

  /* ── Connections (red lines) ──────────────────────────────────── */
  connectionDraft: ConnectionDraft | null;
  startConnection: (fromItemId: number) => void;
  completeConnection: (toItemId: number) => void;
  cancelConnection: () => void;
  removeConnection: (connId: number) => void;
  addingConnection: boolean;

  /* ── Refresh ──────────────────────────────────────────────────── */
  refetch: () => void;
}

export function useBoardState(boardId: number): UseBoardStateReturn {
  const queryClient = useQueryClient();
  const queryKey = ['board-full', boardId] as const;

  // ── Local position overrides (drag-in-progress) ──────────────────
  const [localPositions, setLocalPositions] = useState<
    Record<number, { x: number; y: number }>
  >({});

  const [savePending, setSavePending] = useState(false);
  const batchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingUpdatesRef = useRef<
    Map<number, { x: number; y: number }>
  >(new Map());

  // ── Connection drawing state ─────────────────────────────────────
  const [connectionDraft, setConnectionDraft] =
    useState<ConnectionDraft | null>(null);

  // ── Fetch full board state ───────────────────────────────────────
  const {
    data: boardState,
    isLoading,
    error,
    refetch,
  } = useQuery<FullBoardState>({
    queryKey,
    queryFn: () => boardApi.full(boardId),
    staleTime: BOARD_STALE_TIME,
    gcTime: 5 * 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });

  // ── Helper: invalidate board cache ───────────────────────────────
  const invalidateBoard = useCallback(() => {
    queryClient.invalidateQueries({ queryKey });
  }, [queryClient, queryKey]);

  // ── Get effective position ───────────────────────────────────────
  const getItemPosition = useCallback(
    (item: BoardItem) => {
      const local = localPositions[item.id];
      if (local) return local;
      return { x: item.position_x, y: item.position_y };
    },
    [localPositions],
  );

  // ── Debounced batch coordinate save ──────────────────────────────
  const flushCoordinates = useCallback(() => {
    const updates = pendingUpdatesRef.current;
    if (updates.size === 0) return;

    const items = Array.from(updates.entries()).map(([id, pos]) => ({
      id,
      position_x: pos.x,
      position_y: pos.y,
    }));

    setSavePending(true);
    boardApi
      .batchUpdateCoordinates(boardId, { items })
      .then(() => {
        // Clear local overrides for items that were saved
        setLocalPositions((prev) => {
          const next = { ...prev };
          for (const it of items) delete next[it.id];
          return next;
        });
        invalidateBoard();
      })
      .catch(() => {
        // Keep local positions so the user doesn't see a jump
      })
      .finally(() => {
        setSavePending(false);
      });

    pendingUpdatesRef.current = new Map();
  }, [boardId, invalidateBoard]);

  const onNodeDragEnd = useCallback(
    (itemId: number, x: number, y: number) => {
      // Update local position immediately
      setLocalPositions((prev) => ({ ...prev, [itemId]: { x, y } }));
      pendingUpdatesRef.current.set(itemId, { x, y });

      // Debounce the batch save
      if (batchTimerRef.current) clearTimeout(batchTimerRef.current);
      batchTimerRef.current = setTimeout(flushCoordinates, BATCH_SAVE_DELAY);
    },
    [flushCoordinates],
  );

  // ── Item mutations ───────────────────────────────────────────────
  const addItemMutation = useMutation({
    mutationFn: (data: BoardItemCreateRequest) =>
      boardApi.addItem(boardId, data),
    onSuccess: () => invalidateBoard(),
  });

  const removeItemMutation = useMutation({
    mutationFn: (itemId: number) => boardApi.removeItem(boardId, itemId),
    onSuccess: (_data, itemId) => {
      // Optimistic: remove from local positions
      setLocalPositions((prev) => {
        const next = { ...prev };
        delete next[itemId];
        return next;
      });
      invalidateBoard();
    },
  });

  // ── Note mutations ───────────────────────────────────────────────
  const addNoteMutation = useMutation({
    mutationFn: (data: BoardNoteCreateRequest) =>
      boardApi.addNote(boardId, data),
    onSuccess: () => invalidateBoard(),
  });

  const updateNoteMutation = useMutation({
    mutationFn: ({
      noteId,
      data,
    }: {
      noteId: number;
      data: BoardNoteUpdateRequest;
    }) => boardApi.updateNote(boardId, noteId, data),
    onSuccess: () => invalidateBoard(),
  });

  const deleteNoteMutation = useMutation({
    mutationFn: (noteId: number) => boardApi.deleteNote(boardId, noteId),
    onSuccess: () => invalidateBoard(),
  });

  // ── Connection mutations ─────────────────────────────────────────
  const addConnectionMutation = useMutation({
    mutationFn: (data: BoardConnectionCreateRequest) =>
      boardApi.addConnection(boardId, data),
    onSuccess: () => {
      setConnectionDraft(null);
      invalidateBoard();
    },
  });

  const removeConnectionMutation = useMutation({
    mutationFn: (connId: number) =>
      boardApi.removeConnection(boardId, connId),
    onSuccess: () => invalidateBoard(),
  });

  // ── Connection drawing helpers ───────────────────────────────────
  const startConnection = useCallback((fromItemId: number) => {
    setConnectionDraft({ fromItemId });
  }, []);

  const completeConnection = useCallback(
    (toItemId: number) => {
      if (!connectionDraft) return;
      if (connectionDraft.fromItemId === toItemId) {
        setConnectionDraft(null);
        return;
      }
      addConnectionMutation.mutate({
        from_item: connectionDraft.fromItemId,
        to_item: toItemId,
      });
    },
    [connectionDraft, addConnectionMutation],
  );

  const cancelConnection = useCallback(() => {
    setConnectionDraft(null);
  }, []);

  return {
    boardState,
    isLoading,
    error,
    localPositions,
    getItemPosition,
    onNodeDragEnd,
    savePending,
    addItem: addItemMutation.mutate,
    removeItem: removeItemMutation.mutate,
    addingItem: addItemMutation.isPending,
    addNote: addNoteMutation.mutate,
    updateNote: (noteId: number, data: BoardNoteUpdateRequest) =>
      updateNoteMutation.mutate({ noteId, data }),
    deleteNote: deleteNoteMutation.mutate,
    addingNote: addNoteMutation.isPending,
    connectionDraft,
    startConnection,
    completeConnection,
    cancelConnection,
    removeConnection: removeConnectionMutation.mutate,
    addingConnection: addConnectionMutation.isPending,
    refetch: () => {
      refetch();
    },
  };
}
