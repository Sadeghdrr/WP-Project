/**
 * EvidenceCard — displays evidence details (polymorphic by type).
 *
 * Corrected to match backend detail serializers:
 * - registered_by is PK; use registered_by_name
 * - verified_by is PK; use verified_by_name
 * - No location / collection_date on base model
 * - custody_log is NOT embedded in detail response (fetched separately)
 * - Added document_details display for identity evidence
 */
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import type { EvidenceDetail, EvidenceCustodyLog } from '@/types/evidence.types';

interface EvidenceCardProps {
  evidence: EvidenceDetail;
  custodyLog?: EvidenceCustodyLog[];
}

export function EvidenceCard({ evidence, custodyLog }: EvidenceCardProps) {
  return (
    <Card className="evidence-card">
      <div className="evidence-card__header">
        <h3 className="evidence-card__title">{evidence.title}</h3>
        <Badge variant="info">{evidence.evidence_type_display}</Badge>
        {evidence.is_verified !== undefined && (
          <Badge variant={evidence.is_verified ? 'success' : 'warning'}>
            {evidence.is_verified ? 'Verified' : 'Unverified'}
          </Badge>
        )}
      </div>

      <p className="evidence-card__desc">{evidence.description}</p>

      <div className="evidence-card__meta">
        <span><strong>Case:</strong> #{evidence.case}</span>
        <span><strong>Registered by:</strong> {evidence.registered_by_name ?? '—'}</span>
        <span><strong>Created:</strong> {new Date(evidence.created_at).toLocaleDateString()}</span>
      </div>

      {/* Type-specific details */}
      {evidence.evidence_type === 'testimony' && evidence.statement_text && (
        <div className="evidence-card__section">
          <h4>Statement</h4>
          <p>{evidence.statement_text}</p>
        </div>
      )}

      {evidence.evidence_type === 'biological' && (
        <div className="evidence-card__section">
          <h4>Forensic Result</h4>
          <p>{evidence.forensic_result ?? 'Awaiting analysis'}</p>
          {evidence.verified_by_name && <p><strong>Verified by:</strong> {evidence.verified_by_name}</p>}
        </div>
      )}

      {evidence.evidence_type === 'vehicle' && (
        <div className="evidence-card__section">
          <h4>Vehicle Info</h4>
          <p>Model: {evidence.vehicle_model ?? '—'} | Color: {evidence.color ?? '—'}</p>
          <p>Plate: {evidence.license_plate ?? '—'} | Serial: {evidence.serial_number ?? '—'}</p>
        </div>
      )}

      {evidence.evidence_type === 'identity' && (
        <div className="evidence-card__section">
          <h4>Identity Info</h4>
          <p>Owner: {evidence.owner_full_name ?? '—'}</p>
          {evidence.document_details && Object.keys(evidence.document_details).length > 0 && (
            <div className="evidence-card__doc-details">
              <h5>Document Details</h5>
              <dl>
                {Object.entries(evidence.document_details).map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>
      )}

      {/* Files */}
      {evidence.files?.length > 0 && (
        <div className="evidence-card__section">
          <h4>Files ({evidence.files.length})</h4>
          <ul className="evidence-card__files">
            {evidence.files.map((f) => (
              <li key={f.id}>
                <Badge variant="neutral" size="sm">{f.file_type}</Badge>
                {f.caption || 'Untitled'}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Custody log (passed separately from parent) */}
      {custodyLog && custodyLog.length > 0 && (
        <div className="evidence-card__section">
          <h4>Custody Log</h4>
          <ul className="evidence-card__custody">
            {custodyLog.map((c) => (
              <li key={c.id}>
                <Badge variant="neutral" size="sm">{c.action}</Badge>
                {c.performer_name ?? 'Unknown'} — {new Date(c.timestamp).toLocaleString()}
                {c.details && <span> — {c.details}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
