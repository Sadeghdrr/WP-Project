/**
 * EvidenceVaultPage — paginated evidence list with type/case filters.
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
import { EvidenceTable } from '@/features/evidence/EvidenceTable';
import { evidenceApi } from '@/services/api/evidence.api';
import { EvidencePerms } from '@/config/permissions';
import type { EvidenceType } from '@/types/evidence.types';

const TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'testimony', label: 'Testimony' },
  { value: 'biological', label: 'Biological' },
  { value: 'vehicle', label: 'Vehicle' },
  { value: 'identity', label: 'Identity' },
  { value: 'other', label: 'Other' },
];

const PAGE_SIZE = 20;

export function EvidenceVaultPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [evidenceType, setEvidenceType] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['evidence', { page, evidenceType }],
    queryFn: () =>
      evidenceApi.list({
        page,
        page_size: PAGE_SIZE,
        evidence_type: (evidenceType || undefined) as EvidenceType | undefined,
      }),
  });

  const showSkeleton = useDelayedLoading(isLoading);

  return (
    <div className="page-evidence-vault">
      <div className="page-header">
        <h1 className="page-header__title">Evidence Vault</h1>
        <PermissionGate permissions={[EvidencePerms.ADD_EVIDENCE]}>
          <Button variant="primary" onClick={() => navigate('/evidence/new')}>
            + Register Evidence
          </Button>
        </PermissionGate>
      </div>

      <div className="page-filters">
        <Select
          options={TYPE_OPTIONS}
          value={evidenceType}
          onChange={(e) => { setEvidenceType(e.target.value); setPage(1); }}
          size="sm"
        />
      </div>

      {error && <Alert type="error">Failed to load evidence.</Alert>}

      {showSkeleton ? (
        <TableSkeleton columns={5} rows={8} />
      ) : data ? (
        <>
          <EvidenceTable
            items={data.results}
            onRowClick={(item) => navigate(`/evidence/${item.id}`)}
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
