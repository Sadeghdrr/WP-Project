/**
 * BountyTipForm — submit a bounty tip as a normal user.
 */
import { useState, type FormEvent } from 'react';
import { Input, Textarea } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { bountyTipsApi } from '@/services/api/suspects.api';
import { extractErrorMessage } from '@/utils/errors';
import { useToast } from '@/context/ToastContext';

interface BountyTipFormProps {
  onSuccess?: () => void;
}

export function BountyTipForm({ onSuccess }: BountyTipFormProps) {
  const toast = useToast();
  const [suspectId, setSuspectId] = useState('');
  const [caseId, setCaseId] = useState('');
  const [information, setInformation] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!information.trim()) { setError('Information is required'); return; }
    setError('');
    setLoading(true);
    try {
      await bountyTipsApi.create({
        suspect: suspectId ? Number(suspectId) : undefined,
        case: caseId ? Number(caseId) : undefined,
        information: information.trim(),
      });
      toast.success('Tip submitted successfully');
      setInformation('');
      setSuspectId('');
      setCaseId('');
      onSuccess?.();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="bounty-tip-form" onSubmit={handleSubmit}>
      <h3>Submit a Bounty Tip</h3>
      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      <div className="bounty-tip-form__row">
        <Input label="Suspect ID (optional)" type="number" value={suspectId} onChange={(e) => setSuspectId(e.target.value)} />
        <Input label="Case ID (optional)" type="number" value={caseId} onChange={(e) => setCaseId(e.target.value)} />
      </div>
      <Textarea
        label="Information"
        required
        value={information}
        onChange={(e) => setInformation(e.target.value)}
        rows={5}
        placeholder="Describe what you know about the suspect or case…"
      />
      <Button type="submit" variant="primary" loading={loading}>Submit Tip</Button>
    </form>
  );
}
