/**
 * UserManager — list users, assign roles, activate/deactivate.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Table } from '@/components/ui/Table';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Pagination } from '@/components/ui/Pagination';
import { Alert } from '@/components/ui/Alert';
import { Skeleton } from '@/components/ui/Skeleton';
import { Modal } from '@/components/ui/Modal';
import { usersApi, rolesApi } from '@/services/api/admin.api';
import { extractErrorMessage } from '@/utils/errors';
import { useToast } from '@/context/ToastContext';
import type { Column } from '@/components/ui/Table';
import type { UserListItem, RoleListItem } from '@/types/user.types';

const PAGE_SIZE = 20;

export function UserManager() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [page, setPage] = useState(1);
  const [selectedUser, setSelectedUser] = useState<UserListItem | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState('');
  const [error, setError] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', page],
    queryFn: () => usersApi.list({ page, page_size: PAGE_SIZE }),
  });

  const { data: roles } = useQuery({
    queryKey: ['roles'],
    queryFn: () => rolesApi.list(),
  });

  const assignRoleMutation = useMutation({
    mutationFn: () => usersApi.assignRole(selectedUser!.id, { role_id: Number(selectedRoleId) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast.success('Role assigned');
      setSelectedUser(null);
    },
    onError: (err) => setError(extractErrorMessage(err)),
  });

  const toggleActive = useMutation({
    mutationFn: (user: UserListItem) =>
      user.is_active ? usersApi.deactivate(user.id) : usersApi.activate(user.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast.success('User status updated');
    },
    onError: (err) => setError(extractErrorMessage(err)),
  });

  const columns: Column<UserListItem>[] = [
    { key: 'id', header: 'ID', width: '60px' },
    { key: 'username', header: 'Username' },
    { key: 'email', header: 'Email' },
    { key: 'first_name', header: 'Name', render: (u) => `${u.first_name} ${u.last_name}` },
    {
      key: 'role',
      header: 'Role',
      render: (u) => u.role ? <Badge variant="info" size="sm">{u.role.name}</Badge> : <Badge variant="warning" size="sm">None</Badge>,
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (u) => <Badge variant={u.is_active ? 'success' : 'danger'} size="sm">{u.is_active ? 'Active' : 'Inactive'}</Badge>,
    },
    {
      key: 'actions' as keyof UserListItem,
      header: 'Actions',
      render: (u) => (
        <span className="user-manager__actions">
          <Button size="sm" variant="secondary" onClick={() => { setSelectedUser(u); setSelectedRoleId(u.role?.id.toString() ?? ''); }}>Assign Role</Button>
          <Button size="sm" variant={u.is_active ? 'danger' : 'primary'} onClick={() => toggleActive.mutate(u)}>
            {u.is_active ? 'Deactivate' : 'Activate'}
          </Button>
        </span>
      ),
    },
  ];

  if (isLoading) return <Skeleton height={300} />;

  const roleOptions = (roles ?? []).map((r: RoleListItem) => ({ value: String(r.id), label: r.name }));

  return (
    <div className="user-manager">
      <h3>Users</h3>

      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      {data && (
        <>
          <Table<UserListItem> columns={columns} data={data.results} rowKey={(u) => u.id} />
          <Pagination currentPage={page} totalPages={Math.ceil(data.count / PAGE_SIZE)} onPageChange={setPage} />
        </>
      )}

      <Modal open={!!selectedUser} onClose={() => setSelectedUser(null)} title={`Assign Role — ${selectedUser?.username ?? ''}`}>
        <Select
          label="Role"
          options={roleOptions}
          value={selectedRoleId}
          onChange={(e) => setSelectedRoleId(e.target.value)}
          placeholder="Select a role"
        />
        <Button variant="primary" loading={assignRoleMutation.isPending} onClick={() => assignRoleMutation.mutate()} disabled={!selectedRoleId}>
          Assign
        </Button>
      </Modal>
    </div>
  );
}
