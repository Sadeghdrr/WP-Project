/**
 * EvidenceDetailPage — full evidence detail with coroner verification.
 */
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { Alert } from '@/components/ui/Alert';
import { EvidenceCard } from '@/features/evidence/EvidenceCard';
import { CoronerVerificationForm } from '@/features/evidence/CoronerVerificationForm';
import { PermissionGate } from '@/components/guards/PermissionGate';
import { evidenceApi } from '@/services/api/evidence.api';
import { EvidencePerms } from '@/config/permissions';

export function EvidenceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const evidenceId = Number(id);

  const { data, isLoading, error } = useQuery({
    queryKey: ['evidence', evidenceId],
    queryFn: () => evidenceApi.detail(evidenceId),
    enabled: !Number.isNaN(evidenceId),
  });

  const handleVerified = () => {
    queryClient.invalidateQueries({ queryKey: ['evidence', evidenceId] });
  };

  if (isLoading) return <Skeleton height={500} />;
  if (error || !data) {
    return (
      <div className="page-evidence-detail">
        <Alert type="error">Failed to load evidence #{id}.</Alert>
        <Button variant="secondary" onClick={() => navigate('/evidence')}>Back</Button>
      </div>
    );
  }

  return (
    <div className="page-evidence-detail">
      <div className="page-header">
        <h1 className="page-header__title">Evidence #{data.id}</h1>
        <Button variant="secondary" onClick={() => navigate('/evidence')}>Back</Button>
      </div>

      <EvidenceCard evidence={data} />

      {/* Coroner verification for biological evidence */}
      {data.evidence_type === 'biological' && !data.is_verified && (
        <PermissionGate permissions={[EvidencePerms.CAN_VERIFY_EVIDENCE]}>
          <CoronerVerificationForm evidenceId={evidenceId} onVerified={handleVerified} />
        </PermissionGate>
      )}
    </div>
  );
}
