/**
 * useApiMutation — React Query mutation wrapper with automatic toast feedback.
 *
 * Consistent toast notifications for success / error across all mutations.
 * Eliminates per-page boilerplate: instead of manually wiring onSuccess/onError
 * with useToast in every feature component, consumers call:
 *
 *   const mut = useApiMutation(casesApi.create, {
 *     successMessage: 'Case created',
 *     invalidateKeys: [['cases']],
 *   });
 *
 * Features:
 *  - Auto toast on success / error
 *  - Auto query invalidation
 *  - Extracts human-readable error messages via extractErrorMessage
 *  - Forwards all standard useMutation options
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/hooks/useToast';
import { extractErrorMessage } from '@/utils/errors';

export interface UseApiMutationOptions<TData, TVariables> {
  /** Toast message on success. If omitted, no success toast is shown. */
  successMessage?: string | ((data: TData, variables: TVariables) => string);
  /** Toast message on error. Defaults to extractErrorMessage(). */
  errorMessage?: string;
  /** Query keys to invalidate on success (batched). */
  invalidateKeys?: readonly (readonly unknown[])[];
  /** Extra onSuccess callback (after toast + invalidation). */
  onSuccess?: (data: TData, variables: TVariables) => void;
  /** Extra onError callback (after toast). */
  onError?: (err: unknown, variables: TVariables) => void;
}

export function useApiMutation<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options: UseApiMutationOptions<TData, TVariables> = {},
) {
  const queryClient = useQueryClient();
  const { success, error: showError } = useToast();

  return useMutation({
    mutationFn,
    onSuccess: (data, variables) => {
      // Toast
      if (options.successMessage) {
        const msg =
          typeof options.successMessage === 'function'
            ? options.successMessage(data, variables)
            : options.successMessage;
        success(msg);
      }

      // Invalidate queries
      if (options.invalidateKeys) {
        for (const key of options.invalidateKeys) {
          queryClient.invalidateQueries({ queryKey: key as unknown[] });
        }
      }

      // Forward
      options.onSuccess?.(data, variables);
    },
    onError: (err: unknown, variables: TVariables) => {
      const msg = options.errorMessage ?? extractErrorMessage(err);
      showError(msg);

      // Forward
      options.onError?.(err, variables);
    },
  });
}
