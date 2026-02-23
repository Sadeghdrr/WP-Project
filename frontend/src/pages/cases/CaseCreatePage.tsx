/**
 * CaseCreatePage — wraps CaseForm and navigates to the new case on success.
 */
import { useNavigate } from 'react-router-dom';
import { CaseForm } from '@/features/cases/CaseForm';
import type { CaseDetail } from '@/types/case.types';

export function CaseCreatePage() {
  const navigate = useNavigate();

  const handleSuccess = (created: CaseDetail) => {
    navigate(`/cases/${created.id}`);
  };

  return (
    <div className="page-case-create">
      <div className="page-header">
        <h1 className="page-header__title">Create New Case</h1>
      </div>
      <CaseForm onSuccess={handleSuccess} />
    </div>
  );
}
