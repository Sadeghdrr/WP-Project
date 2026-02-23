/**
 * RoleManager — list, create, and edit roles + assign permissions.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Input, Textarea } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Alert } from '@/components/ui/Alert';
import { Skeleton } from '@/components/ui/Skeleton';
import { Modal } from '@/components/ui/Modal';
import { rolesApi, permissionsApi } from '@/services/api/admin.api';
import { extractErrorMessage } from '@/utils/errors';
import type { Role, Permission } from '@/types/user.types';

export function RoleManager() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [hierarchyLevel, setHierarchyLevel] = useState('0');
  const [selectedPerms, setSelectedPerms] = useState<number[]>([]);
  const [error, setError] = useState('');

  const { data: roles, isLoading } = useQuery({
    queryKey: ['roles'],
    queryFn: () => rolesApi.list(),
  });

  const { data: allPermissions } = useQuery({
    queryKey: ['permissions'],
    queryFn: () => permissionsApi.list(),
  });

  const createMutation = useMutation({
    mutationFn: () => rolesApi.create({ name, description, hierarchy_level: Number(hierarchyLevel) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      resetForm();
    },
    onError: (err) => setError(extractErrorMessage(err)),
  });

  const updateMutation = useMutation({
    mutationFn: () => rolesApi.update(editingRole!.id, { name, description, hierarchy_level: Number(hierarchyLevel) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      resetForm();
    },
    onError: (err) => setError(extractErrorMessage(err)),
  });

  const permMutation = useMutation({
    mutationFn: (roleId: number) => rolesApi.assignPermissions(roleId, { permissions: selectedPerms }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['roles'] }),
    onError: (err) => setError(extractErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => rolesApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['roles'] }),
    onError: (err) => setError(extractErrorMessage(err)),
  });

  const resetForm = () => {
    setShowCreate(false);
    setEditingRole(null);
    setName('');
    setDescription('');
    setHierarchyLevel('0');
    setSelectedPerms([]);
    setError('');
  };

  const openEdit = (role: Role) => {
    setEditingRole(role);
    setName(role.name);
    setDescription(role.description);
    setHierarchyLevel(String(role.hierarchy_level));
    setSelectedPerms(role.permissions.map((p: Permission) => p.id));
    setShowCreate(true);
  };

  const togglePerm = (id: number) => {
    setSelectedPerms((prev) => prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]);
  };

  if (isLoading) return <Skeleton height={200} />;

  return (
    <div className="role-manager">
      <div className="role-manager__header">
        <h3>Roles</h3>
        <Button size="sm" variant="primary" onClick={() => { resetForm(); setShowCreate(true); }}>+ New Role</Button>
      </div>

      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      <ul className="role-manager__list">
        {roles?.map((r) => (
          <li key={r.id} className="role-manager__item">
            <span className="role-manager__name">{r.name}</span>
            <Badge variant="neutral" size="sm">Level {r.hierarchy_level}</Badge>
            <Button size="sm" variant="secondary" onClick={() => {
              rolesApi.detail(r.id).then(openEdit);
            }}>Edit</Button>
            <Button size="sm" variant="danger" onClick={() => deleteMutation.mutate(r.id)}>Delete</Button>
          </li>
        ))}
      </ul>

      <Modal open={showCreate} onClose={resetForm} title={editingRole ? 'Edit Role' : 'Create Role'}>
        <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
        <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
        <Input label="Hierarchy Level" type="number" value={hierarchyLevel} onChange={(e) => setHierarchyLevel(e.target.value)} />

        {allPermissions && (
          <div className="role-manager__perms">
            <h4>Permissions</h4>
            <div className="role-manager__perm-grid">
              {allPermissions.map((p) => (
                <label key={p.id} className="role-manager__perm-label">
                  <input type="checkbox" checked={selectedPerms.includes(p.id)} onChange={() => togglePerm(p.id)} />
                  {p.codename}
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="role-manager__modal-actions">
          {editingRole ? (
            <>
              <Button variant="primary" loading={updateMutation.isPending} onClick={() => updateMutation.mutate()}>Save Changes</Button>
              <Button variant="secondary" loading={permMutation.isPending} onClick={() => permMutation.mutate(editingRole.id)}>Save Permissions</Button>
            </>
          ) : (
            <Button variant="primary" loading={createMutation.isPending} onClick={() => createMutation.mutate()}>Create Role</Button>
          )}
        </div>
      </Modal>
    </div>
  );
}
