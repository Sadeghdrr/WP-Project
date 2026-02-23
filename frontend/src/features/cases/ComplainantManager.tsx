/**
 * ComplainantManager — list, add, and review complainants on a case.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { Skeleton } from '@/components/ui/Skeleton';
import { usePermissions } from '@/hooks/usePermissions';
import { casesApi } from '@/services/api/cases.api';
import { CasesPerms } from '@/config/permissions';
import { extractErrorMessage } from '@/utils/errors';

interface ComplainantManagerProps {
  caseId: number;
}

export function ComplainantManager({ caseId }: ComplainantManagerProps) {
  const queryClient = useQueryClient();
  const { hasPermission } = usePermissions();
  const [userId, setUserId] = useState('');
  const [error, setError] = useState('');

  const { data: complainants, isLoading } = useQuery({
    queryKey: ['cases', caseId, 'complainants'],
    queryFn: () => casesApi.complainants(caseId),
  });

  const addMutation = useMutation({
    mutationFn: (uid: number) => casesApi.addComplainant(caseId, { user_id: uid }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', caseId, 'complainants'] });
      setUserId('');
      setError('');
    },
    onError: (err) => setError(extractErrorMessage(err)),
  });

  const reviewMutation = useMutation({
    mutationFn: ({ complainantId, action }: { complainantId: number; action: 'approve' | 'reject' }) =>
      casesApi.reviewComplainant(caseId, complainantId, { action }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', caseId, 'complainants'] });
    },
    onError: (err) => setError(extractErrorMessage(err)),
  });

  const canReview = hasPermission(CasesPerms.CAN_REVIEW_COMPLAINT);

  const statusVariant = (s: string) =>
    s === 'approved' ? 'success' : s === 'rejected' ? 'danger' : 'warning';

  if (isLoading) return <Skeleton height={120} />;

  return (
    <div className="complainant-manager">
      <h3 className="complainant-manager__title">Complainants</h3>

      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      {complainants && complainants.length > 0 ? (
        <ul className="complainant-manager__list">
          {complainants.map((c) => (
            <li key={c.id} className="complainant-manager__item">
              <span className="complainant-manager__name">
                {c.user.first_name} {c.user.last_name}
                {c.is_primary && <Badge variant="info" size="sm">Primary</Badge>}
              </span>
              <Badge variant={statusVariant(c.status)} size="sm">{c.status}</Badge>

              {canReview && c.status === 'pending' && (
                <span className="complainant-manager__actions">
                  <Button
                    size="sm"
                    variant="primary"
                    loading={reviewMutation.isPending}
                    onClick={() => reviewMutation.mutate({ complainantId: c.id, action: 'approve' })}
                  >
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="danger"
                    loading={reviewMutation.isPending}
                    onClick={() => reviewMutation.mutate({ complainantId: c.id, action: 'reject' })}
                  >
                    Reject
                  </Button>
                </span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="complainant-manager__empty">No complainants registered.</p>
      )}

      {/* Add complainant */}
      <div className="complainant-manager__add">
        <Input
          label="Add Complainant (User ID)"
          type="number"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="Enter user ID"
          size="sm"
        />
        <Button
          size="sm"
          variant="secondary"
          loading={addMutation.isPending}
          disabled={!userId}
          onClick={() => addMutation.mutate(Number(userId))}
        >
          Add
        </Button>
      </div>
    </div>
  );
}
