/**
 * CaseDetailsPage — full case detail view with timeline, review, complainants.
 */
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DetailSkeleton } from '@/components/ui/SkeletonPresets';
import { Alert } from '@/components/ui/Alert';
import { useDelayedLoading } from '@/hooks/useDelayedLoading';
import { CaseTimeline } from '@/features/cases/CaseTimeline';
import { CaseReviewActions } from '@/features/cases/CaseReviewActions';
import { ComplainantManager } from '@/features/cases/ComplainantManager';
import { WitnessManager } from '@/features/cases/WitnessManager';

import { casesApi } from '@/services/api/cases.api';

const CRIME_LEVEL_LABELS: Record<number, string> = {
  1: 'Level 3 (Minor)',
  2: 'Level 2 (Moderate)',
  3: 'Level 1 (Serious)',
  4: 'Critical',
};

export function CaseDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const caseId = Number(id);

  const { data: caseData, isLoading, error } = useQuery({
    queryKey: ['cases', caseId],
    queryFn: () => casesApi.detail(caseId),
    enabled: !Number.isNaN(caseId),
  });

  const showSkeleton = useDelayedLoading(isLoading);

  const handleUpdate = () => {
    queryClient.invalidateQueries({ queryKey: ['cases', caseId] });
  };

  if (showSkeleton) return <DetailSkeleton sections={4} />;
  if (error || !caseData) {
    return (
      <div className="page-case-detail">
        <Alert type="error">Failed to load case #{id}.</Alert>
        <Button variant="secondary" onClick={() => navigate('/cases')}>
          Back to Cases
        </Button>
      </div>
    );
  }

  return (
    <div className="page-case-detail">
      <div className="page-header">
        <div>
          <h1 className="page-header__title">
            Case #{caseData.id}: {caseData.title}
          </h1>
          <div className="page-header__meta">
            <Badge variant="info">{caseData.status.replace(/_/g, ' ')}</Badge>
            <Badge variant={caseData.crime_level >= 3 ? 'danger' : 'warning'}>
              {CRIME_LEVEL_LABELS[caseData.crime_level] ?? `Level ${caseData.crime_level}`}
            </Badge>
            <Badge variant="neutral">{caseData.creation_type}</Badge>
          </div>
        </div>
        <Button variant="secondary" onClick={() => navigate('/cases')}>
          Back
        </Button>
      </div>

      {/* Case Information */}
      <Card>
        <div className="case-info-grid">
          <div>
            <strong>Description</strong>
            <p>{caseData.description}</p>
          </div>
          <div>
            <strong>Location</strong>
            <p>{caseData.location || '—'}</p>
          </div>
          <div>
            <strong>Incident Date</strong>
            <p>{caseData.incident_date ?? '—'}</p>
          </div>
          <div>
            <strong>Created By</strong>
            <p>{caseData.created_by.first_name} {caseData.created_by.last_name}</p>
          </div>
          <div>
            <strong>Detective</strong>
            <p>
              {caseData.assigned_detective
                ? `${caseData.assigned_detective.first_name} ${caseData.assigned_detective.last_name}`
                : '—'}
            </p>
          </div>
          <div>
            <strong>Rejection Count</strong>
            <p>{caseData.rejection_count}</p>
          </div>
        </div>
      </Card>

      {/* Calculations */}
      {caseData.calculations && (
        <Card>
          <h3>Case Metrics</h3>
          <div className="case-info-grid">
            <div><strong>Crime Degree</strong><p>{caseData.calculations.crime_level_degree}</p></div>
            <div><strong>Days Since Creation</strong><p>{caseData.calculations.days_since_creation}</p></div>
            <div><strong>Tracking Threshold</strong><p>{caseData.calculations.tracking_threshold}</p></div>
            <div><strong>Reward (Rials)</strong><p>{caseData.calculations.reward_rials.toLocaleString()}</p></div>
          </div>
        </Card>
      )}

      {/* Review actions */}
      <CaseReviewActions caseData={caseData} onUpdate={handleUpdate} />

      {/* Complainants */}
      <ComplainantManager caseId={caseId} />

      {/* Witnesses (editable for active cases, read-only for closed/voided) */}
      <WitnessManager
        caseId={caseId}
        readOnly={caseData.status === 'closed' || caseData.status === 'voided'}
      />

      {/* Rejection warning (§4.2.1 — 3 rejections → voided) */}
      {caseData.rejection_count > 0 && caseData.status !== 'voided' && (
        <Alert type="warning">
          This case has been returned {caseData.rejection_count} time(s).
          {caseData.rejection_count >= 2 && ' One more rejection will void the case.'}
        </Alert>
      )}

      {caseData.status === 'voided' && (
        <Alert type="error">
          This case has been voided after {caseData.rejection_count} rejection(s).
        </Alert>
      )}

      {/* Status Timeline */}
      {caseData.status_logs.length > 0 && (
        <Card>
          <h3>Timeline</h3>
          <CaseTimeline logs={caseData.status_logs} />
        </Card>
      )}
    </div>
  );
}
