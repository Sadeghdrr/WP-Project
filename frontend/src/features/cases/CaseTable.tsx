/**
 * CaseTable — filterable table of cases with pagination.
 */
import { Table, type Column } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import type { CaseListItem } from '@/types/case.types';

interface CaseTableProps {
  cases: CaseListItem[];
  loading: boolean;
  onRowClick: (c: CaseListItem) => void;
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
  onSort?: (col: string) => void;
}

const crimeLevelLabel: Record<number, string> = {
  1: 'Level 3 (Minor)',
  2: 'Level 2 (Medium)',
  3: 'Level 1 (Major)',
  4: 'Critical',
};

const statusVariant = (status: string): 'success' | 'warning' | 'danger' | 'info' | 'neutral' => {
  if (['closed'].includes(status)) return 'success';
  if (['voided'].includes(status)) return 'danger';
  if (['open', 'investigation'].includes(status)) return 'info';
  return 'warning';
};

export function CaseTable({
  cases,
  loading,
  onRowClick,
  sortColumn,
  sortDirection,
  onSort,
}: CaseTableProps) {
  const columns: Column<CaseListItem>[] = [
    { key: 'id', header: 'ID', width: '60px', sortable: true },
    { key: 'title', header: 'Title', sortable: true },
    {
      key: 'crime_level',
      header: 'Crime Level',
      width: '140px',
      render: (r) => crimeLevelLabel[r.crime_level] ?? `Level ${r.crime_level}`,
    },
    {
      key: 'status',
      header: 'Status',
      width: '160px',
      render: (r) => (
        <Badge variant={statusVariant(r.status)}>
          {r.status.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    {
      key: 'creation_type',
      header: 'Type',
      width: '120px',
      render: (r) => r.creation_type === 'complaint' ? 'Complaint' : 'Crime Scene',
    },
    {
      key: 'incident_date',
      header: 'Incident',
      width: '120px',
      sortable: true,
      render: (r) => r.incident_date ? new Date(r.incident_date).toLocaleDateString() : '—',
    },
  ];

  return (
    <Table<CaseListItem>
      columns={columns}
      data={cases}
      rowKey={(r) => r.id}
      loading={loading}
      emptyMessage="No cases found"
      onRowClick={onRowClick}
      sortColumn={sortColumn}
      sortDirection={sortDirection}
      onSort={onSort}
    />
  );
}
