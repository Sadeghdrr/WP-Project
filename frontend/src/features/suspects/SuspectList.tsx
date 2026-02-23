/**
 * SuspectList — tabular suspect list using generic Table component.
 */
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import type { Column } from '@/components/ui/Table';
import type { SuspectListItem } from '@/types/suspect.types';

interface SuspectListProps {
  suspects: SuspectListItem[];
  onRowClick?: (s: SuspectListItem) => void;
}

export function SuspectList({ suspects, onRowClick }: SuspectListProps) {
  const columns: Column<SuspectListItem>[] = [
    { key: 'id', header: 'ID', width: '60px' },
    { key: 'full_name', header: 'Name' },
    { key: 'national_id', header: 'National ID' },
    {
      key: 'status',
      header: 'Status',
      render: (s) => (
        <Badge variant={s.status === 'convicted' ? 'danger' : s.status === 'released' || s.status === 'acquitted' ? 'success' : 'warning'} size="sm">
          {s.status.replace(/_/g, ' ')}
        </Badge>
      ),
    },
    { key: 'case', header: 'Case #', width: '80px' },
    { key: 'most_wanted_score', header: 'Wanted Score', width: '100px' },
  ];

  return (
    <Table<SuspectListItem>
      columns={columns}
      data={suspects}
      rowKey={(s) => s.id}
      onRowClick={onRowClick}
      emptyMessage="No suspects found."
    />
  );
}
