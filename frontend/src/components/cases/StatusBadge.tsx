/**
 * Status badge — color-coded by case status.
 * Mirrors backend CaseStatus enum.
 */

import React from 'react';
import type { CaseStatusValue } from '../../types/case.types';

const STATUS_COLORS: Record<CaseStatusValue, string> = {
  complaint_registered: 'bg-amber-500/30 text-amber-200 border-amber-500/50',
  cadet_review: 'bg-blue-500/30 text-blue-200 border-blue-500/50',
  returned_to_complainant: 'bg-orange-500/30 text-orange-200 border-orange-500/50',
  officer_review: 'bg-indigo-500/30 text-indigo-200 border-indigo-500/50',
  returned_to_cadet: 'bg-yellow-500/30 text-yellow-200 border-yellow-500/50',
  voided: 'bg-red-500/30 text-red-200 border-red-500/50',
  pending_approval: 'bg-purple-500/30 text-purple-200 border-purple-500/50',
  open: 'bg-emerald-500/30 text-emerald-200 border-emerald-500/50',
  investigation: 'bg-cyan-500/30 text-cyan-200 border-cyan-500/50',
  suspect_identified: 'bg-teal-500/30 text-teal-200 border-teal-500/50',
  sergeant_review: 'bg-sky-500/30 text-sky-200 border-sky-500/50',
  arrest_ordered: 'bg-rose-500/30 text-rose-200 border-rose-500/50',
  interrogation: 'bg-violet-500/30 text-violet-200 border-violet-500/50',
  captain_review: 'bg-fuchsia-500/30 text-fuchsia-200 border-fuchsia-500/50',
  chief_review: 'bg-pink-500/30 text-pink-200 border-pink-500/50',
  judiciary: 'bg-slate-500/30 text-slate-200 border-slate-500/50',
  closed: 'bg-slate-600/30 text-slate-300 border-slate-600/50',
};

export interface StatusBadgeProps {
  status: CaseStatusValue;
  displayText?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  displayText,
}) => {
  const colorClass = STATUS_COLORS[status] ?? 'bg-slate-500/30 text-slate-200';
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${colorClass}`}
    >
      {displayText ?? status}
    </span>
  );
};
