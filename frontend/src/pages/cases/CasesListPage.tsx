/**
 * Cases list page — role-based view.
 * Complainant: own cases; Cadet: cadet_review; Officer: officer_review.
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listCases } from '../../services/api/cases.api';
import { usePermissions } from '../../hooks/usePermissions';
import { StatusBadge } from '../../components/cases/StatusBadge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { CasesPerms } from '../../config/permissions';
import type { CaseListItem } from '../../types/case.types';
import { CaseStatus } from '../../types/case.types';

export const CasesListPage: React.FC = () => {
  const { hasPermission } = usePermissions();
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<string | null>(null);

  const canCreate = hasPermission(CasesPerms.ADD_CASE);
  const isCadet = hasPermission(CasesPerms.CAN_REVIEW_COMPLAINT);
  const isOfficer = hasPermission(CasesPerms.CAN_APPROVE_CASE);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (filter) params.status = filter;
    if (isCadet && !filter) params.status = CaseStatus.CADET_REVIEW;
    if (isOfficer && !isCadet && filter) params.status = filter;

    listCases(params)
      .then(setCases)
      .catch(() => setCases([]))
      .finally(() => setIsLoading(false));
  }, [filter, isCadet, isOfficer]);

  return (
    <div>
      <div className="mb-6 flex flex-row-reverse items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-100">
          {isCadet ? 'پرونده‌های در انتظار بررسی کارآموز' : isOfficer ? 'پرونده‌های در انتظار بررسی افسر' : 'پرونده‌های من'}
        </h1>
        {canCreate && (
          <Link to="/cases/new">
            <Button variant="primary">ثبت شکایت جدید</Button>
          </Link>
        )}
      </div>

      <div className="mb-4 flex gap-2">
        {isOfficer && (
          <>
            <button
              onClick={() => setFilter(null)}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                !filter ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300'
              }`}
            >
              همه
            </button>
            <button
              onClick={() => setFilter(CaseStatus.PENDING_APPROVAL)}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                filter === CaseStatus.PENDING_APPROVAL ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300'
              }`}
            >
              صحنه جرم (در انتظار تأیید)
            </button>
          </>
        )}
        {!isCadet && !isOfficer && (
          <>
            <button
              onClick={() => setFilter(null)}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                !filter ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300'
              }`}
            >
              همه
            </button>
            <button
              onClick={() => setFilter(CaseStatus.COMPLAINT_REGISTERED)}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                filter === CaseStatus.COMPLAINT_REGISTERED ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300'
              }`}
            >
              ثبت شده
            </button>
            <button
              onClick={() => setFilter(CaseStatus.CADET_REVIEW)}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                filter === CaseStatus.CADET_REVIEW ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300'
              }`}
            >
              در بررسی کارآموز
            </button>
            <button
              onClick={() => setFilter(CaseStatus.RETURNED_TO_COMPLAINANT)}
              className={`rounded-lg px-4 py-2 text-sm font-medium ${
                filter === CaseStatus.RETURNED_TO_COMPLAINANT ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-300'
              }`}
            >
              برگشت داده شده
            </button>
          </>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
        </div>
      ) : cases.length === 0 ? (
        <Card>
          <p className="text-center text-slate-500">پرونده‌ای یافت نشد.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {cases.map((c) => (
            <Link key={c.id} to={`/cases/${c.id}`}>
              <Card className="cursor-pointer transition-colors hover:border-slate-600">
                <div className="flex flex-row-reverse items-center justify-between">
                  <div className="text-right">
                    <h3 className="font-medium text-slate-200">{c.title}</h3>
                    <p className="text-sm text-slate-500">
                      {c.crime_level_display} • {c.complainant_count} شاکی
                    </p>
                  </div>
                  <StatusBadge status={c.status} displayText={c.status_display} />
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};
