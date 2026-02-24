/**
 * CaseCreatePage — wraps CaseForm and navigates to the new case on success.
 * Route-level guard ensures only users with add_case can access.
 * Page-level PermissionGate provides defense-in-depth.
 */
import { useNavigate } from 'react-router-dom';
import { CaseForm } from '@/features/cases/CaseForm';
import { PermissionGate } from '@/components/guards/PermissionGate';
import { Alert } from '@/components/ui/Alert';
import { CasesPerms } from '@/config/permissions';
import type { CaseDetail } from '@/types/case.types';

export function CaseCreatePage() {
  const navigate = useNavigate();

  const handleSuccess = (created: CaseDetail) => {
    navigate(`/cases/${created.id}`);
  };

  return (
    <PermissionGate
      permissions={[CasesPerms.ADD_CASE]}
      fallback={
        <div style={{ padding: '3rem', maxWidth: '480px', margin: '4rem auto' }}>
          <Alert type="error" title="403 — Forbidden">
            You do not have permission to create cases.
          </Alert>
        </div>
      }
    >
      <div className="page-case-create">
        <div className="page-header">
          <h1 className="page-header__title">Create New Case</h1>
        </div>
        <CaseForm onSuccess={handleSuccess} />
      </div>
    </PermissionGate>
  );
}
