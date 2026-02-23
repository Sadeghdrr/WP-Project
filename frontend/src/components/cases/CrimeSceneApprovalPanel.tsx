/**
 * Approval panel for crime-scene cases.
 * Backend approve_crime_scene only supports approve (no reject).
 * PENDING_APPROVAL → OPEN
 */

import React from 'react';
import { approveCrimeScene } from '../../services/api/cases.api';
import { Button } from '../ui/Button';

export interface CrimeSceneApprovalPanelProps {
  caseId: number;
  onApproved: () => void;
  isLoading: boolean;
  setLoading: (v: boolean) => void;
  setError: (v: string | null) => void;
}

export const CrimeSceneApprovalPanel: React.FC<CrimeSceneApprovalPanelProps> = ({
  caseId,
  onApproved,
  isLoading,
  setLoading,
  setError,
}) => {
  const handleApprove = async () => {
    setError(null);
    setLoading(true);
    try {
      await approveCrimeScene(caseId);
      onApproved();
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(
        axiosError.response?.data?.detail ?? 'خطا در تأیید پرونده.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
      <h3 className="mb-4 text-right font-medium text-slate-200">
        تأیید پرونده صحنه جرم
      </h3>
      <p className="mb-4 text-right text-sm text-slate-400">
        این پرونده توسط یک درجه پلیس ثبت شده و در انتظار تأیید شماست. با
        تأیید، پرونده به‌طور رسمی باز می‌شود.
      </p>
      <Button
        variant="primary"
        onClick={handleApprove}
        loading={isLoading}
      >
        تأیید و باز کردن پرونده
      </Button>
    </div>
  );
};
