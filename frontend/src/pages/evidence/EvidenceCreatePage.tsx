/**
 * EvidenceCreatePage — wraps EvidenceForm, navigates on success.
 */
import { useNavigate } from 'react-router-dom';
import { EvidenceForm } from '@/features/evidence/EvidenceForm';
import type { EvidenceDetail } from '@/types/evidence.types';

export function EvidenceCreatePage() {
  const navigate = useNavigate();

  const handleSuccess = (created: EvidenceDetail) => {
    navigate(`/evidence/${created.id}`);
  };

  return (
    <div className="page-evidence-create">
      <div className="page-header">
        <h1 className="page-header__title">Register New Evidence</h1>
      </div>
      <EvidenceForm onSuccess={handleSuccess} />
    </div>
  );
}
