/**
 * Review action panel — approve/reject with required message on reject.
 * Used by Cadet and Officer review panels.
 */

import React, { useState } from 'react';
import { Button } from '../ui/Button';
import type { ReviewDecisionRequest } from '../../types/case.types';

export interface ReviewActionPanelProps {
  onApprove: () => void | Promise<void>;
  onReject: (message: string) => void | Promise<void>;
  isLoading?: boolean;
  approveLabel?: string;
  rejectLabel?: string;
}

export const ReviewActionPanel: React.FC<ReviewActionPanelProps> = ({
  onApprove,
  onReject,
  isLoading = false,
  approveLabel = 'تأیید',
  rejectLabel = 'رد',
}) => {
  const [rejectMessage, setRejectMessage] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [rejectError, setRejectError] = useState<string | null>(null);

  const handleReject = async () => {
    const trimmed = rejectMessage.trim();
    if (!trimmed) {
      setRejectError('لطفاً دلیل رد را وارد کنید.');
      return;
    }
    setRejectError(null);
    await onReject(trimmed);
    setShowRejectForm(false);
    setRejectMessage('');
  };

  return (
    <div className="space-y-4 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
      <h3 className="text-right font-medium text-slate-200">اقدام بررسی</h3>
      {showRejectForm ? (
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-right text-sm text-slate-400">
              دلیل رد (الزامی)
            </label>
            <textarea
              value={rejectMessage}
              onChange={(e) => {
                setRejectMessage(e.target.value);
                setRejectError(null);
              }}
              className="w-full rounded-lg border border-slate-600 bg-slate-800/50 px-3 py-2 text-right text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              rows={4}
              placeholder="دلیل رد را به شاکی یا افسر ارجاع‌دهنده اطلاع دهید..."
              disabled={isLoading}
            />
            {rejectError && (
              <p className="mt-1 text-sm text-red-400">{rejectError}</p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant="danger"
              onClick={handleReject}
              loading={isLoading}
              disabled={!rejectMessage.trim()}
            >
              {rejectLabel}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setShowRejectForm(false);
                setRejectMessage('');
                setRejectError(null);
              }}
              disabled={isLoading}
            >
              انصراف
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex gap-2">
          <Button
            variant="primary"
            onClick={onApprove}
            loading={isLoading}
          >
            {approveLabel}
          </Button>
          <Button
            variant="danger"
            onClick={() => setShowRejectForm(true)}
            disabled={isLoading}
          >
            {rejectLabel}
          </Button>
        </div>
      )}
    </div>
  );
};
