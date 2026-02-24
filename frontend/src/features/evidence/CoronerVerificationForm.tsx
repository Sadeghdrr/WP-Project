/**
 * CoronerVerificationForm — lets coroners verify biological evidence.
 *
 * Backend VerifyBiologicalEvidenceSerializer expects:
 *   { decision: "approve" | "reject", forensic_result: string, notes: string }
 */
import { useState, type FormEvent } from 'react';
import { Textarea } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { evidenceApi } from '@/services/api/evidence.api';
import { extractErrorMessage } from '@/utils/errors';
import { useToast } from '@/context/ToastContext';

interface CoronerVerificationFormProps {
  evidenceId: number;
  onVerified: () => void;
}

export function CoronerVerificationForm({ evidenceId, onVerified }: CoronerVerificationFormProps) {
  const toast = useToast();
  const [forensicResult, setForensicResult] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleDecision = async (decision: 'approve' | 'reject', e: FormEvent) => {
    e.preventDefault();
    if (!forensicResult.trim()) {
      setError('Forensic result is required.');
      return;
    }
    if (decision === 'reject' && !notes.trim()) {
      setError('Notes are required when rejecting evidence.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await evidenceApi.verify(evidenceId, {
        decision,
        forensic_result: forensicResult.trim(),
        notes: notes.trim() || undefined,
      });
      toast.success(decision === 'approve' ? 'Evidence approved' : 'Evidence rejected');
      onVerified();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="coroner-form">
      <h3 className="coroner-form__title">Coroner Verification</h3>

      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      <Textarea
        label="Forensic Examination Result"
        required
        value={forensicResult}
        onChange={(e) => setForensicResult(e.target.value)}
        rows={4}
        placeholder="Enter forensic analysis findings…"
      />

      <Textarea
        label="Notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={3}
        placeholder="Optional notes (required for rejection)…"
      />

      <div className="coroner-form__actions">
        <Button variant="primary" loading={loading} onClick={(e) => handleDecision('approve', e)}>
          Approve
        </Button>
        <Button variant="danger" loading={loading} onClick={(e) => handleDecision('reject', e)}>
          Reject
        </Button>
      </div>
    </form>
  );
}
