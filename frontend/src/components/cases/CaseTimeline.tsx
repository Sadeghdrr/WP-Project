/**
 * Timeline view for case status progress.
 * Displays status_logs from backend.
 */

import React from 'react';
import type { CaseStatusLog } from '../../types/case.types';

export interface CaseTimelineProps {
  statusLogs: CaseStatusLog[];
}

export const CaseTimeline: React.FC<CaseTimelineProps> = ({ statusLogs }) => {
  if (statusLogs.length === 0) {
    return (
      <p className="text-sm text-slate-500">هنوز تغییری در وضعیت ثبت نشده است.</p>
    );
  }

  return (
    <div className="space-y-4">
      {statusLogs.map((log, index) => (
        <div key={log.id} className="flex gap-4">
          <div className="flex flex-col items-center">
            <div className="h-3 w-3 rounded-full bg-blue-500" />
            {index < statusLogs.length - 1 && (
              <div className="mt-1 h-full w-0.5 flex-1 bg-slate-600" />
            )}
          </div>
          <div className="flex-1 pb-4">
            <p className="text-sm font-medium text-slate-200">
              {log.from_status || 'شروع'} → {log.to_status}
            </p>
            <p className="text-xs text-slate-500">
              {log.changed_by_name ?? 'سیستم'} •{' '}
              {new Date(log.created_at).toLocaleString('fa-IR')}
            </p>
            {log.message && (
              <p className="mt-1 rounded-lg bg-slate-800/50 p-2 text-sm text-slate-300">
                {log.message}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};
