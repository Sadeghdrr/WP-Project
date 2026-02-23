/**
 * EvidenceTable — tabular evidence list using generic Table component.
 */
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import type { Column } from '@/components/ui/Table';
import type { EvidenceListItem } from '@/types/evidence.types';

const TYPE_LABELS: Record<string, string> = {
  testimony: 'Testimony',
  biological: 'Biological',
  vehicle: 'Vehicle',
  identity: 'Identity',
  other: 'Other',
};

interface EvidenceTableProps {
  items: EvidenceListItem[];
  onRowClick?: (item: EvidenceListItem) => void;
}

export function EvidenceTable({ items, onRowClick }: EvidenceTableProps) {
  const columns: Column<EvidenceListItem>[] = [
    { key: 'id', header: 'ID', width: '60px' },
    { key: 'title', header: 'Title' },
    {
      key: 'evidence_type',
      header: 'Type',
      render: (row) => (
        <Badge variant="info" size="sm">
          {TYPE_LABELS[row.evidence_type] ?? row.evidence_type}
        </Badge>
      ),
    },
    { key: 'case', header: 'Case #', width: '80px' },
    {
      key: 'registered_by',
      header: 'Registered By',
      render: (row) =>
        `${row.registered_by.first_name} ${row.registered_by.last_name}`,
    },
    {
      key: 'verification_status',
      header: 'Verified',
      render: (row) => (
        <Badge
          variant={row.verification_status === 'verified' ? 'success' : 'warning'}
          size="sm"
        >
          {row.verification_status ?? 'Pending'}
        </Badge>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (row) => new Date(row.created_at).toLocaleDateString(),
    },
  ];

  return (
    <Table<EvidenceListItem>
      columns={columns}
      data={items}
      rowKey={(r) => r.id}
      onRowClick={onRowClick}
      emptyMessage="No evidence found."
    />
  );
}
