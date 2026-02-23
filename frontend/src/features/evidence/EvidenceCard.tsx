/**
 * EvidenceCard — displays evidence details (polymorphic by type).
 */
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import type { EvidenceDetail } from '@/types/evidence.types';

const TYPE_LABELS: Record<string, string> = {
  testimony: 'Testimony',
  biological: 'Biological',
  vehicle: 'Vehicle',
  identity: 'Identity',
  other: 'Other',
};

interface EvidenceCardProps {
  evidence: EvidenceDetail;
}

export function EvidenceCard({ evidence }: EvidenceCardProps) {
  return (
    <Card className="evidence-card">
      <div className="evidence-card__header">
        <h3 className="evidence-card__title">{evidence.title}</h3>
        <Badge variant="info">{TYPE_LABELS[evidence.evidence_type] ?? evidence.evidence_type}</Badge>
        {evidence.is_verified !== undefined && (
          <Badge variant={evidence.is_verified ? 'success' : 'warning'}>
            {evidence.is_verified ? 'Verified' : 'Unverified'}
          </Badge>
        )}
      </div>

      <p className="evidence-card__desc">{evidence.description}</p>

      <div className="evidence-card__meta">
        <span><strong>Case:</strong> #{evidence.case}</span>
        <span><strong>Location:</strong> {evidence.location || '—'}</span>
        <span><strong>Collection:</strong> {evidence.collection_date ?? '—'}</span>
        <span><strong>Registered by:</strong> {evidence.registered_by.first_name} {evidence.registered_by.last_name}</span>
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
          {evidence.verified_by && <p><strong>Verified by:</strong> {evidence.verified_by.first_name} {evidence.verified_by.last_name}</p>}
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
        </div>
      )}

      {/* Files */}
      {evidence.files.length > 0 && (
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

      {/* Custody log */}
      {evidence.custody_log.length > 0 && (
        <div className="evidence-card__section">
          <h4>Custody Log</h4>
          <ul className="evidence-card__custody">
            {evidence.custody_log.map((c) => (
              <li key={c.id}>
                <Badge variant="neutral" size="sm">{c.action_type}</Badge>
                {c.handled_by.first_name} {c.handled_by.last_name} — {new Date(c.timestamp).toLocaleString()}
                {c.notes && <span> — {c.notes}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}
