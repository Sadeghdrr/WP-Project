/**
 * TrialForm — judge records a verdict for a suspect.
 */
import { useState, type FormEvent } from 'react';
import { Input, Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { trialsApi } from '@/services/api/suspects.api';
import { extractErrorMessage } from '@/utils/errors';
import { useToast } from '@/context/ToastContext';
import type { VerdictChoice } from '@/types/suspect.types';

const VERDICT_OPTIONS = [
  { value: 'guilty', label: 'Guilty' },
  { value: 'not_guilty', label: 'Not Guilty' },
];

interface TrialFormProps {
  suspectId: number;
  onSuccess: () => void;
}

export function TrialForm({ suspectId, onSuccess }: TrialFormProps) {
  const toast = useToast();
  const [verdict, setVerdict] = useState('');
  const [sentence, setSentence] = useState('');
  const [notes, setNotes] = useState('');
  const [trialDate, setTrialDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!verdict) { setError('Verdict is required'); return; }
    setError('');
    setLoading(true);
    try {
      await trialsApi.create(suspectId, {
        verdict: verdict as VerdictChoice,
        sentence: sentence || undefined,
        notes: notes || undefined,
        trial_date: trialDate || undefined,
      });
      toast.success('Trial recorded');
      onSuccess();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="trial-form" onSubmit={handleSubmit}>
      <h3>Record Trial Verdict</h3>
      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      <Select label="Verdict" required options={VERDICT_OPTIONS} value={verdict} onChange={(e) => setVerdict(e.target.value)} placeholder="Select verdict" />
      {verdict === 'guilty' && (
        <Input label="Sentence" value={sentence} onChange={(e) => setSentence(e.target.value)} placeholder="Punishment description" />
      )}
      <Input label="Trial Date" type="date" value={trialDate} onChange={(e) => setTrialDate(e.target.value)} />
      <Textarea label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
      <Button type="submit" variant="primary" loading={loading}>Record Verdict</Button>
    </form>
  );
}
