/**
 * AdminPanelPage — role & user management via Tabs.
 */
import { Tabs } from '@/components/ui/Tabs';
import { RoleManager } from '@/features/admin/RoleManager';
import { UserManager } from '@/features/admin/UserManager';

export function AdminPanelPage() {
  const tabs = [
    { key: 'roles', label: 'Roles', content: <RoleManager /> },
    { key: 'users', label: 'Users', content: <UserManager /> },
  ];

  return (
    <div className="page-admin">
      <div className="page-header">
        <h1 className="page-header__title">Admin Panel</h1>
      </div>
      <Tabs tabs={tabs} defaultActiveKey="roles" />
    </div>
  );
}
