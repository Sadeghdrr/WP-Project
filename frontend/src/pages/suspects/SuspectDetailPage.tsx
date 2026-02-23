/**
 * SuspectDetailPage — full suspect detail with interrogation, trial, bail.
 */
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { Alert } from '@/components/ui/Alert';
import { PermissionGate } from '@/components/guards/PermissionGate';
import { InterrogationForm } from '@/features/suspects/InterrogationForm';
import { TrialForm } from '@/features/suspects/TrialForm';
import { BailPaymentForm } from '@/features/suspects/BailPaymentForm';
import { suspectsApi } from '@/services/api/suspects.api';
import { SuspectsPerms } from '@/config/permissions';

export function SuspectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const suspectId = Number(id);

  const { data: suspect, isLoading, error } = useQuery({
    queryKey: ['suspects', suspectId],
    queryFn: () => suspectsApi.detail(suspectId),
    enabled: !Number.isNaN(suspectId),
  });

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['suspects', suspectId] });
  };

  if (isLoading) return <Skeleton height={600} />;
  if (error || !suspect) {
    return (
      <div className="page-suspect-detail">
        <Alert type="error">Failed to load suspect #{id}.</Alert>
        <Button variant="secondary" onClick={() => navigate('/suspects')}>Back</Button>
      </div>
    );
  }

  return (
    <div className="page-suspect-detail">
      <div className="page-header">
        <div>
          <h1 className="page-header__title">{suspect.full_name}</h1>
          <div className="page-header__meta">
            <Badge variant="warning">{suspect.status.replace(/_/g, ' ')}</Badge>
            <Badge variant="neutral">Case #{suspect.case}</Badge>
          </div>
        </div>
        <Button variant="secondary" onClick={() => navigate('/suspects')}>Back</Button>
      </div>

      {/* Suspect Info */}
      <Card>
        <div className="case-info-grid">
          <div><strong>National ID</strong><p>{suspect.national_id}</p></div>
          <div><strong>Date of Birth</strong><p>{suspect.date_of_birth ?? '—'}</p></div>
          <div><strong>Phone</strong><p>{suspect.phone_number || '—'}</p></div>
          <div><strong>Address</strong><p>{suspect.address || '—'}</p></div>
          <div><strong>Aliases</strong><p>{suspect.aliases || '—'}</p></div>
          <div><strong>Days Wanted</strong><p>{suspect.days_wanted}</p></div>
          <div><strong>Reward</strong><p>{suspect.reward_amount.toLocaleString()} Rials</p></div>
          <div><strong>Most Wanted Score</strong><p>{suspect.most_wanted_score}</p></div>
        </div>
        {suspect.description && <p style={{ marginTop: '0.5rem' }}>{suspect.description}</p>}
        {suspect.photo && <img src={suspect.photo} alt={suspect.full_name} style={{ maxWidth: 200, marginTop: '0.5rem', borderRadius: 8 }} />}
      </Card>

      {/* Interrogations */}
      {suspect.interrogations.length > 0 && (
        <Card>
          <h3>Interrogations ({suspect.interrogations.length})</h3>
          <ul className="interrogation-list">
            {suspect.interrogations.map((i) => (
              <li key={i.id}>
                <strong>Score: {i.score}/10</strong> — {i.technique || 'Standard'} —
                {i.conducted_by.first_name} {i.conducted_by.last_name} —
                {new Date(i.created_at).toLocaleDateString()}
                {i.duration_minutes ? ` (${i.duration_minutes} min)` : ''}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Record interrogation */}
      <PermissionGate permissions={[SuspectsPerms.CAN_CONDUCT_INTERROGATION]}>
        <Card>
          <InterrogationForm suspectId={suspectId} onSuccess={handleRefresh} />
        </Card>
      </PermissionGate>

      {/* Trials */}
      {suspect.trials.length > 0 && (
        <Card>
          <h3>Trials ({suspect.trials.length})</h3>
          <ul className="trial-list">
            {suspect.trials.map((t) => (
              <li key={t.id}>
                <Badge variant={t.verdict === 'guilty' ? 'danger' : 'success'} size="sm">{t.verdict}</Badge>
                {t.sentence && <span> — {t.sentence}</span>}
                <span> — Judge: {t.judge.first_name} {t.judge.last_name}</span>
                <span> — {t.trial_date}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Record trial */}
      <PermissionGate permissions={[SuspectsPerms.CAN_JUDGE_TRIAL]}>
        <Card>
          <TrialForm suspectId={suspectId} onSuccess={handleRefresh} />
        </Card>
      </PermissionGate>

      {/* Bail */}
      <BailPaymentForm suspectId={suspectId} bails={suspect.bails} onPaymentComplete={handleRefresh} />
    </div>
  );
}
