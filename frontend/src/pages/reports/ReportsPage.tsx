/**
 * ReportsPage — list cases, click to view full report.
 * Primarily for Judge, Captain, and Police Chief (§5.7).
 * Route-level guard enforces can_forward_to_judiciary.
 * Page-level PermissionGate provides defense-in-depth.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Pagination } from '@/components/ui/Pagination';
import { Alert } from '@/components/ui/Alert';
import { Skeleton } from '@/components/ui/Skeleton';
import { Button } from '@/components/ui/Button';
import { CaseReport } from '@/features/reports/CaseReport';
import { CaseTable } from '@/features/cases/CaseTable';
import { PermissionGate } from '@/components/guards/PermissionGate';
import { CasesPerms } from '@/config/permissions';
import { casesApi } from '@/services/api/cases.api';
import type { CaseListItem } from '@/types/case.types';

const PAGE_SIZE = 15;

export function ReportsPage() {
  const [page, setPage] = useState(1);
  const [selectedCase, setSelectedCase] = useState<CaseListItem | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['cases-reports', page],
    queryFn: () => casesApi.list({ page, page_size: PAGE_SIZE }),
  });

  if (selectedCase) {
    return (
      <PermissionGate
        permissions={[CasesPerms.CAN_FORWARD_TO_JUDICIARY]}
        fallback={
          <div style={{ padding: '3rem', maxWidth: '480px', margin: '4rem auto' }}>
            <Alert type="error" title="403 — Forbidden">
              You do not have permission to view reports.
            </Alert>
          </div>
        }
      >
        <div className="page-reports">
          <div className="page-header">
            <h1 className="page-header__title">Report: Case #{selectedCase.id}</h1>
            <Button variant="secondary" onClick={() => setSelectedCase(null)}>Back to List</Button>
          </div>
          <CaseReport caseId={selectedCase.id} />
        </div>
      </PermissionGate>
    );
  }

  return (
    <PermissionGate
      permissions={[CasesPerms.CAN_FORWARD_TO_JUDICIARY]}
      fallback={
        <div style={{ padding: '3rem', maxWidth: '480px', margin: '4rem auto' }}>
          <Alert type="error" title="403 — Forbidden">
            You do not have permission to view reports.
          </Alert>
        </div>
      }
    >
    <div className="page-reports">
      <div className="page-header">
        <h1 className="page-header__title">General Reports</h1>
      </div>

      {error && <Alert type="error">Failed to load cases.</Alert>}
      {isLoading ? (
        <Skeleton height={400} />
      ) : data ? (
        <>
          <CaseTable cases={data.results} loading={false} onRowClick={setSelectedCase} />
          <Pagination
            currentPage={page}
            totalPages={Math.ceil(data.count / PAGE_SIZE)}
            onPageChange={setPage}
          />
        </>
      ) : null}
    </div>
    </PermissionGate>
  );
}
