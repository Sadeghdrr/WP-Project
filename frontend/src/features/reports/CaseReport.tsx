/**
 * CaseReport — renders the full report for a single case.
 *
 * Fetches the case report endpoint and displays all sections:
 * case info, personnel, complainants, witnesses, evidence, suspects,
 * status history, and calculations.
 */
import { useQuery } from '@tanstack/react-query';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Alert } from '@/components/ui/Alert';
import { casesApi } from '@/services/api/cases.api';

interface CaseReportProps {
  caseId: number;
}

export function CaseReport({ caseId }: CaseReportProps) {
  const { data: report, isLoading, error } = useQuery({
    queryKey: ['cases', caseId, 'report'],
    queryFn: () => casesApi.report(caseId),
  });

  if (isLoading) return <Skeleton height={400} />;
  if (error || !report) return <Alert type="error">Failed to load report.</Alert>;

  // The report object shape comes from the backend CaseReportSerializer
  const r = report as Record<string, unknown>;
  const caseInfo = r.case as Record<string, unknown> | undefined;
  const personnel = r.personnel as Record<string, unknown> | undefined;
  const complainants = (r.complainants ?? []) as Array<Record<string, unknown>>;
  const witnesses = (r.witnesses ?? []) as Array<Record<string, unknown>>;
  const evidence = (r.evidence ?? []) as Array<Record<string, unknown>>;
  const suspects = (r.suspects ?? []) as Array<Record<string, unknown>>;
  const statusHistory = (r.status_history ?? []) as Array<Record<string, unknown>>;
  const calculations = r.calculations as Record<string, unknown> | undefined;

  return (
    <div className="case-report">
      {/* Case info */}
      {caseInfo && (
        <Card className="case-report__section">
          <h3>Case Information</h3>
          <p><strong>Title:</strong> {String(caseInfo.title ?? '')}</p>
          <p><strong>Status:</strong> <Badge variant="info">{String(caseInfo.status ?? '')}</Badge></p>
          <p><strong>Description:</strong> {String(caseInfo.description ?? '')}</p>
          <p><strong>Created:</strong> {String(caseInfo.created_at ?? '')}</p>
        </Card>
      )}

      {/* Personnel */}
      {personnel && (
        <Card className="case-report__section">
          <h3>Personnel</h3>
          {Object.entries(personnel).map(([key, val]) => (
            <p key={key}><strong>{key.replace(/_/g, ' ')}:</strong> {val ? String((val as Record<string, unknown>).first_name ?? '') + ' ' + String((val as Record<string, unknown>).last_name ?? '') : '—'}</p>
          ))}
        </Card>
      )}

      {/* Complainants */}
      {complainants.length > 0 && (
        <Card className="case-report__section">
          <h3>Complainants ({complainants.length})</h3>
          <ul>{complainants.map((c, i) => <li key={i}>{String((c.user as Record<string, unknown>)?.first_name ?? '')} {String((c.user as Record<string, unknown>)?.last_name ?? '')} — {String(c.status ?? '')}</li>)}</ul>
        </Card>
      )}

      {/* Witnesses */}
      {witnesses.length > 0 && (
        <Card className="case-report__section">
          <h3>Witnesses ({witnesses.length})</h3>
          <ul>{witnesses.map((w, i) => <li key={i}>{String(w.full_name ?? '')} — {String(w.national_id ?? '')}</li>)}</ul>
        </Card>
      )}

      {/* Evidence */}
      {evidence.length > 0 && (
        <Card className="case-report__section">
          <h3>Evidence ({evidence.length})</h3>
          <ul>{evidence.map((e, i) => <li key={i}><Badge variant="neutral" size="sm">{String(e.evidence_type ?? '')}</Badge> {String(e.title ?? '')}</li>)}</ul>
        </Card>
      )}

      {/* Suspects */}
      {suspects.length > 0 && (
        <Card className="case-report__section">
          <h3>Suspects ({suspects.length})</h3>
          <ul>{suspects.map((s, i) => <li key={i}>{String(s.full_name ?? '')} — <Badge variant="warning" size="sm">{String(s.status ?? '')}</Badge></li>)}</ul>
        </Card>
      )}

      {/* Status History */}
      {statusHistory.length > 0 && (
        <Card className="case-report__section">
          <h3>Status History</h3>
          <ul>
            {statusHistory.map((sh, i) => (
              <li key={i}>
                {String(sh.from_status ?? '')} → {String(sh.to_status ?? '')} — {String(sh.created_at ?? '')}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* Calculations */}
      {calculations && (
        <Card className="case-report__section">
          <h3>Calculations</h3>
          {Object.entries(calculations).map(([key, val]) => (
            <p key={key}><strong>{key.replace(/_/g, ' ')}:</strong> {String(val)}</p>
          ))}
        </Card>
      )}
    </div>
  );
}
