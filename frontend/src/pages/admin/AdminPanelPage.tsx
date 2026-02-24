/**
 * AdminPanelPage — role & user management via Tabs.
 * Route-level guard ensures only System Administrators can access.
 * Page-level PermissionGate provides defense-in-depth.
 */
import { Tabs } from '@/components/ui/Tabs';
import { RoleManager } from '@/features/admin/RoleManager';
import { UserManager } from '@/features/admin/UserManager';
import { PermissionGate } from '@/components/guards/PermissionGate';
import { Alert } from '@/components/ui/Alert';
import { AccountsPerms } from '@/config/permissions';

export function AdminPanelPage() {
  const tabs = [
    { key: 'roles', label: 'Roles', content: <RoleManager /> },
    { key: 'users', label: 'Users', content: <UserManager /> },
  ];

  return (
    <PermissionGate
      permissions={[AccountsPerms.ADD_ROLE, AccountsPerms.CHANGE_ROLE]}
      fallback={
        <div style={{ padding: '3rem', maxWidth: '480px', margin: '4rem auto' }}>
          <Alert type="error" title="403 — Forbidden">
            You do not have permission to access the admin panel.
          </Alert>
        </div>
      }
    >
      <div className="page-admin">
        <div className="page-header">
          <h1 className="page-header__title">Admin Panel</h1>
        </div>
        <Tabs tabs={tabs} defaultActiveKey="roles" />
      </div>
    </PermissionGate>
  );
}
