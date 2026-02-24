/**
 * EvidenceTable — tabular evidence list using generic Table component.
 *
 * Corrected to match backend EvidenceListSerializer:
 * - registered_by is PK (number); display via registered_by_name
 * - Removed phantom verification_status column (not in list serializer)
 * - Uses evidence_type_display from backend
 */
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import type { Column } from '@/components/ui/Table';
import type { EvidenceListItem } from '@/types/evidence.types';

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
          {row.evidence_type_display}
        </Badge>
      ),
    },
    { key: 'case', header: 'Case #', width: '80px' },
    {
      key: 'registered_by',
      header: 'Registered By',
      render: (row) => row.registered_by_name ?? '—',
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
