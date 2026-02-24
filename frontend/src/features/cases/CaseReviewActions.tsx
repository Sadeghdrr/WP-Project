/**
 * CaseReviewActions — role-based approve/reject/return buttons.
 *
 * Determines available actions from the case's current status
 * and the user's permissions. No role names are hardcoded —
 * permission codenames drive the logic.
 */
import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Input';
import { Alert } from '@/components/ui/Alert';
import { usePermissions } from '@/hooks/usePermissions';
import { useToast } from '@/context/ToastContext';
import { casesApi } from '@/services/api/cases.api';
import { CasesPerms } from '@/config/permissions';
import { extractErrorMessage } from '@/utils/errors';
import type { CaseDetail } from '@/types/case.types';

interface CaseReviewActionsProps {
  caseData: CaseDetail;
  onUpdate: () => void;
}

export function CaseReviewActions({ caseData, onUpdate }: CaseReviewActionsProps) {
  const { hasPermission } = usePermissions();
  const toast = useToast();
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState('');
  const [error, setError] = useState('');

  const status = caseData.status;

  const handleAction = async (
    action: () => Promise<unknown>,
    label: string,
  ) => {
    setError('');
    setLoading(label);
    try {
      await action();
      toast.success(`Case ${label.toLowerCase()} successfully`);
      setMessage('');
      onUpdate();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading('');
    }
  };

  const actions: { label: string; variant: 'primary' | 'danger' | 'secondary'; action: () => Promise<unknown>; visible: boolean }[] = [];

  // Submit for review (complainant who owns the case)
  if (status === 'complaint_registered') {
    actions.push({
      label: 'Submit for Review',
      variant: 'primary',
      action: () => casesApi.submit(caseData.id),
      visible: true,
    });
  }

  // Resubmit (when returned to complainant)
  if (status === 'returned_to_complainant') {
    actions.push({
      label: 'Resubmit',
      variant: 'primary',
      action: () => casesApi.resubmit(caseData.id, { description: message || undefined }),
      visible: true,
    });
  }

  // Cadet re-forward (when officer returned to cadet — §4.2.1)
  if (status === 'returned_to_cadet' && hasPermission(CasesPerms.CAN_REVIEW_COMPLAINT)) {
    actions.push({
      label: 'Re-forward to Officer',
      variant: 'primary',
      action: () => casesApi.transition(caseData.id, { target_status: 'officer_review' }),
      visible: true,
    });
  }

  // Cadet review
  if (status === 'cadet_review' && hasPermission(CasesPerms.CAN_REVIEW_COMPLAINT)) {
    actions.push({
      label: 'Approve (Cadet)',
      variant: 'primary',
      action: () => casesApi.cadetReview(caseData.id, { decision: 'approve' }),
      visible: true,
    });
    actions.push({
      label: 'Return (Cadet)',
      variant: 'danger',
      action: () => casesApi.cadetReview(caseData.id, { decision: 'reject', message }),
      visible: true,
    });
  }

  // Officer review
  if (status === 'officer_review' && hasPermission(CasesPerms.CAN_APPROVE_CASE)) {
    actions.push({
      label: 'Approve (Officer)',
      variant: 'primary',
      action: () => casesApi.officerReview(caseData.id, { decision: 'approve' }),
      visible: true,
    });
    actions.push({
      label: 'Return (Officer)',
      variant: 'danger',
      action: () => casesApi.officerReview(caseData.id, { decision: 'reject', message }),
      visible: true,
    });
  }

  // Crime scene approval
  if (status === 'pending_approval' && hasPermission(CasesPerms.CAN_APPROVE_CASE)) {
    actions.push({
      label: 'Approve Crime Scene',
      variant: 'primary',
      action: () => casesApi.approveCrimeScene(caseData.id),
      visible: true,
    });
  }

  // Sergeant review (suspect identification)
  if (status === 'sergeant_review' && hasPermission(CasesPerms.CAN_CHANGE_CASE_STATUS)) {
    actions.push({
      label: 'Approve (Sergeant)',
      variant: 'primary',
      action: () => casesApi.sergeantReview(caseData.id, { decision: 'approve' }),
      visible: true,
    });
    actions.push({
      label: 'Reject (Sergeant)',
      variant: 'danger',
      action: () => casesApi.sergeantReview(caseData.id, { decision: 'reject', message }),
      visible: true,
    });
  }

  // Forward to judiciary (Captain handles non-critical, Captain/Chief handle critical)
  if (status === 'captain_review' && hasPermission(CasesPerms.CAN_FORWARD_TO_JUDICIARY)) {
    actions.push({
      label: 'Forward to Judiciary',
      variant: 'primary',
      action: () => casesApi.forwardJudiciary(caseData.id),
      visible: true,
    });
  }

  // Chief review (critical cases only — §4.2 / §4.4)
  if (status === 'chief_review' && hasPermission(CasesPerms.CAN_APPROVE_CRITICAL_CASE)) {
    actions.push({
      label: 'Approve & Forward to Judiciary',
      variant: 'primary',
      action: () => casesApi.forwardJudiciary(caseData.id),
      visible: true,
    });
  }

  const visibleActions = actions.filter((a) => a.visible);
  if (visibleActions.length === 0) return null;

  return (
    <div className="case-review-actions">
      <h3 className="case-review-actions__title">Actions</h3>

      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      {visibleActions.some((a) => a.label.includes('Return') || a.label.includes('Reject') || a.label === 'Resubmit') && (
        <Textarea
          label="Message (for returns/rejections)"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Reason for return or rejection…"
        />
      )}

      <div className="case-review-actions__buttons">
        {visibleActions.map((a) => (
          <Button
            key={a.label}
            variant={a.variant}
            loading={loading === a.label}
            disabled={!!loading}
            onClick={() => handleAction(a.action, a.label)}
          >
            {a.label}
          </Button>
        ))}
      </div>
    </div>
  );
}
