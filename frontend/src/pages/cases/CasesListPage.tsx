/**
 * CasesListPage — paginated, filtered list of cases.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Pagination } from '@/components/ui/Pagination';
import { Alert } from '@/components/ui/Alert';
import { TableSkeleton } from '@/components/ui/SkeletonPresets';
import { PermissionGate } from '@/components/guards/PermissionGate';
import { useDelayedLoading } from '@/hooks/useDelayedLoading';
import { CaseTable } from '@/features/cases/CaseTable';
import { casesApi } from '@/services/api/cases.api';
import { CasesPerms } from '@/config/permissions';
import type { CaseStatus, CrimeLevel, CaseCreationType } from '@/types/case.types';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'complaint_registered', label: 'Complaint Registered' },
  { value: 'cadet_review', label: 'Cadet Review' },
  { value: 'returned_to_complainant', label: 'Returned to Complainant' },
  { value: 'officer_review', label: 'Officer Review' },
  { value: 'returned_to_cadet', label: 'Returned to Cadet' },
  { value: 'pending_approval', label: 'Pending Approval' },
  { value: 'open', label: 'Open' },
  { value: 'investigation', label: 'Investigation' },
  { value: 'suspect_identified', label: 'Suspect Identified' },
  { value: 'closed', label: 'Closed' },
  { value: 'voided', label: 'Voided' },
];

const CRIME_LEVEL_OPTIONS = [
  { value: '', label: 'All Levels' },
  { value: '1', label: 'Level 3 (Minor)' },
  { value: '2', label: 'Level 2 (Moderate)' },
  { value: '3', label: 'Level 1 (Serious)' },
  { value: '4', label: 'Critical' },
];

const TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'complaint', label: 'Complaint' },
  { value: 'crime_scene', label: 'Crime Scene' },
];

const PAGE_SIZE = 20;

export function CasesListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [crimeLevel, setCrimeLevel] = useState('');
  const [creationType, setCreationType] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['cases', { page, status, crimeLevel, creationType }],
    queryFn: () =>
      casesApi.list({
        page,
        page_size: PAGE_SIZE,
        status: (status || undefined) as CaseStatus | undefined,
        crime_level: (crimeLevel ? Number(crimeLevel) : undefined) as CrimeLevel | undefined,
        creation_type: (creationType || undefined) as CaseCreationType | undefined,
      }),
  });

  const showSkeleton = useDelayedLoading(isLoading);

  return (
    <div className="page-cases-list">
      <div className="page-header">
        <h1 className="page-header__title">Cases</h1>
        <PermissionGate permissions={[CasesPerms.ADD_CASE]}>
          <Button variant="primary" onClick={() => navigate('/cases/new')}>
            + New Case
          </Button>
        </PermissionGate>
      </div>

      {/* Filters */}
      <div className="page-filters">
        <Select
          options={STATUS_OPTIONS}
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          size="sm"
        />
        <Select
          options={CRIME_LEVEL_OPTIONS}
          value={crimeLevel}
          onChange={(e) => { setCrimeLevel(e.target.value); setPage(1); }}
          size="sm"
        />
        <Select
          options={TYPE_OPTIONS}
          value={creationType}
          onChange={(e) => { setCreationType(e.target.value); setPage(1); }}
          size="sm"
        />
      </div>

      {/* Content */}
      {error && <Alert type="error">Failed to load cases.</Alert>}

      {showSkeleton ? (
        <TableSkeleton columns={6} rows={8} />
      ) : data ? (
        <>
          <CaseTable
            cases={data.results}
            loading={isLoading}
            onRowClick={(c) => navigate(`/cases/${c.id}`)}
          />
          <Pagination
            currentPage={page}
            totalPages={Math.ceil(data.count / PAGE_SIZE)}
            onPageChange={setPage}
          />
        </>
      ) : null}
    </div>
  );
}
