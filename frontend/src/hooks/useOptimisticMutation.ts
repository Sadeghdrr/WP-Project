/**
 * useOptimisticMutation — React Query mutation with optimistic cache update.
 *
 * Wraps useMutation with an onMutate that:
 *  1. Cancels running queries for the target key
 *  2. Snapshots the current cache value
 *  3. Applies the optimistic updater to the cache
 *  4. Returns the snapshot for rollback
 *
 * On error → rolls back to snapshot.
 * On settle → invalidates the key to refetch server truth.
 *
 * Appropriate use-cases (selective — not everywhere):
 *  - Board node position updates (drag & drop)
 *  - Board connection removal
 *  - Board note inline edits
 *  - Marking items (e.g., toggling status)
 *
 * NOT appropriate for:
 *  - Creating new entities (ID unknown until server responds)
 *  - Complex state transitions (e.g., case status changes)
 *  - Financial operations (bail payments)
 *
 * Usage:
 *   const mutation = useOptimisticMutation({
 *     mutationFn: (id) => boardApi.removeConnection(boardId, id),
 *     queryKey: ['board-full', boardId],
 *     updater: (old, removedId) => ({
 *       ...old,
 *       connections: old.connections.filter(c => c.id !== removedId),
 *     }),
 *     successMessage: 'Connection removed',
 *   });
 */
import {
  useMutation,
  useQueryClient,
  type QueryKey,
} from '@tanstack/react-query';
import { useToast } from '@/hooks/useToast';
import { extractErrorMessage } from '@/utils/errors';

interface UseOptimisticMutationOptions<TData, TVariables, TCacheData> {
  /** The async function to perform the mutation. */
  mutationFn: (variables: TVariables) => Promise<TData>;
  /** The query key whose cache will be optimistically updated. */
  queryKey: QueryKey;
  /**
   * Produces the new cache value from the current value + mutation variables.
   * Return undefined to skip the optimistic update.
   */
  updater: (
    currentData: TCacheData,
    variables: TVariables,
  ) => TCacheData | undefined;
  /** Optional toast on success. */
  successMessage?: string;
  /** Optional toast on error. Defaults to auto-extract. */
  errorMessage?: string;
  /** Callback after success. */
  onSuccess?: (data: TData, variables: TVariables) => void;
}

export function useOptimisticMutation<TData, TVariables, TCacheData>({
  mutationFn,
  queryKey,
  updater,
  successMessage,
  errorMessage,
  onSuccess,
}: UseOptimisticMutationOptions<TData, TVariables, TCacheData>) {
  const queryClient = useQueryClient();
  const { success, error: showError } = useToast();

  return useMutation<TData, unknown, TVariables, { previous: TCacheData | undefined }>({
    mutationFn,
    onMutate: async (variables) => {
      // 1. Cancel in-flight queries
      await queryClient.cancelQueries({ queryKey });

      // 2. Snapshot current cache
      const previous = queryClient.getQueryData<TCacheData>(queryKey);

      // 3. Optimistically update
      if (previous !== undefined) {
        const next = updater(previous, variables);
        if (next !== undefined) {
          queryClient.setQueryData<TCacheData>(queryKey, next);
        }
      }

      return { previous };
    },
    onError: (err, _variables, onMutateResult) => {
      // Rollback
      if (onMutateResult?.previous !== undefined) {
        queryClient.setQueryData<TCacheData>(queryKey, onMutateResult.previous);
      }
      showError(errorMessage ?? extractErrorMessage(err));
    },
    onSuccess: (data, variables) => {
      if (successMessage) success(successMessage);
      onSuccess?.(data, variables);
    },
    onSettled: () => {
      // Always refetch to sync with server truth
      queryClient.invalidateQueries({ queryKey });
    },
  });
}
