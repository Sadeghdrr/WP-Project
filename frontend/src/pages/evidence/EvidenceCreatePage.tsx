/**
 * EvidenceCreatePage — wraps EvidenceForm, navigates on success.
 * Route-level guard ensures only users with add_evidence can access.
 * Page-level PermissionGate provides defense-in-depth.
 */
import { useNavigate } from 'react-router-dom';
import { EvidenceForm } from '@/features/evidence/EvidenceForm';
import { PermissionGate } from '@/components/guards/PermissionGate';
import { Alert } from '@/components/ui/Alert';
import { EvidencePerms } from '@/config/permissions';
import type { EvidenceDetail } from '@/types/evidence.types';

export function EvidenceCreatePage() {
  const navigate = useNavigate();

  const handleSuccess = (created: EvidenceDetail) => {
    navigate(`/evidence/${created.id}`);
  };

  return (
    <PermissionGate
      permissions={[EvidencePerms.ADD_EVIDENCE]}
      fallback={
        <div style={{ padding: '3rem', maxWidth: '480px', margin: '4rem auto' }}>
          <Alert type="error" title="403 — Forbidden">
            You do not have permission to register evidence.
          </Alert>
        </div>
      }
    >
      <div className="page-evidence-create">
        <div className="page-header">
          <h1 className="page-header__title">Register New Evidence</h1>
        </div>
        <EvidenceForm onSuccess={handleSuccess} />
      </div>
    </PermissionGate>
  );
}
