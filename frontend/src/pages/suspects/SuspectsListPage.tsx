/**
 * SuspectsListPage — paginated, filtered suspect list.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Select } from '@/components/ui/Select';
import { Pagination } from '@/components/ui/Pagination';
import { Alert } from '@/components/ui/Alert';
import { Skeleton } from '@/components/ui/Skeleton';
import { SuspectList } from '@/features/suspects/SuspectList';
import { suspectsApi } from '@/services/api/suspects.api';
import type { SuspectStatus } from '@/types/suspect.types';

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'wanted', label: 'Wanted' },
  { value: 'in_custody', label: 'In Custody' },
  { value: 'under_interrogation', label: 'Under Interrogation' },
  { value: 'under_trial', label: 'Under Trial' },
  { value: 'convicted', label: 'Convicted' },
  { value: 'released', label: 'Released' },
  { value: 'acquitted', label: 'Acquitted' },
];

const PAGE_SIZE = 20;

export function SuspectsListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['suspects', { page, status }],
    queryFn: () =>
      suspectsApi.list({
        page,
        page_size: PAGE_SIZE,
        status: (status || undefined) as SuspectStatus | undefined,
      }),
  });

  return (
    <div className="page-suspects-list">
      <div className="page-header">
        <h1 className="page-header__title">Suspects</h1>
      </div>

      <div className="page-filters">
        <Select
          options={STATUS_OPTIONS}
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          size="sm"
        />
      </div>

      {error && <Alert type="error">Failed to load suspects.</Alert>}

      {isLoading ? (
        <Skeleton height={400} />
      ) : data ? (
        <>
          <SuspectList
            suspects={data.results}
            onRowClick={(s) => navigate(`/suspects/${s.id}`)}
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
