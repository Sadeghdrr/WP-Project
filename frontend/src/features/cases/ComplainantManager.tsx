/**
 * Complainant management — list complainants, Cadet approves/rejects each.
 * Used in Cadet review panel.
 */

import React from 'react';
import { Button } from '../../components/ui/Button';
import { StatusBadge } from '../../components/cases/StatusBadge';
import type { CaseComplainant } from '../../types/case.types';
import { ComplainantStatus } from '../../types/case.types';

export interface ComplainantManagerProps {
  complainants: CaseComplainant[];
  onReview: (complainantId: number, decision: 'approve' | 'reject') => void | Promise<void>;
  canReview: boolean;
  isLoading?: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'در انتظار',
  approved: 'تأیید شده',
  rejected: 'رد شده',
};

export const ComplainantManager: React.FC<ComplainantManagerProps> = ({
  complainants,
  onReview,
  canReview,
  isLoading = false,
}) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case ComplainantStatus.APPROVED:
        return 'bg-emerald-500/30 text-emerald-200';
      case ComplainantStatus.REJECTED:
        return 'bg-red-500/30 text-red-200';
      default:
        return 'bg-amber-500/30 text-amber-200';
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-right font-medium text-slate-200">شاکیان</h3>
      {complainants.length === 0 ? (
        <p className="text-sm text-slate-500">شاکی‌ای ثبت نشده است.</p>
      ) : (
        <div className="space-y-3">
          {complainants.map((c) => (
            <div
              key={c.id}
              className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-800/50 p-4"
            >
              <div className="text-right">
                <p className="font-medium text-slate-200">{c.user_display}</p>
                <p className="text-xs text-slate-500">
                  {c.is_primary ? 'شاکی اصلی' : 'شاکی اضافی'}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusColor(c.status)}`}
                >
                  {STATUS_LABELS[c.status] ?? c.status}
                </span>
                {canReview && c.status === ComplainantStatus.PENDING && (
                  <div className="flex gap-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => onReview(c.id, 'approve')}
                      disabled={isLoading}
                    >
                      تأیید
                    </Button>
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => onReview(c.id, 'reject')}
                      disabled={isLoading}
                    >
                      رد
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
