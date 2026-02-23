/**
 * CoronerVerificationForm — lets coroners verify biological evidence.
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleVerify = async (isVerified: boolean, e: FormEvent) => {
    e.preventDefault();
    if (!forensicResult.trim()) {
      setError('Forensic result is required.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await evidenceApi.verify(evidenceId, {
        forensic_result: forensicResult.trim(),
        is_verified: isVerified,
      });
      toast.success(isVerified ? 'Evidence verified' : 'Evidence marked unverified');
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

      <div className="coroner-form__actions">
        <Button variant="primary" loading={loading} onClick={(e) => handleVerify(true, e)}>
          Verify
        </Button>
        <Button variant="danger" loading={loading} onClick={(e) => handleVerify(false, e)}>
          Reject
        </Button>
      </div>
    </form>
  );
}
