/**
 * TrialForm — judge records a verdict for a suspect.
 *
 * Uses useApiMutation for automatic toast feedback and error handling.
 */
import { useState, type FormEvent } from 'react';
import { Input, Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { trialsApi } from '@/services/api/suspects.api';
import { useApiMutation } from '@/hooks/useApiMutation';
import { extractErrorMessage } from '@/utils/errors';
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
  const [verdict, setVerdict] = useState('');
  const [sentence, setSentence] = useState('');
  const [notes, setNotes] = useState('');
  const [trialDate, setTrialDate] = useState('');
  const [validationError, setValidationError] = useState('');

  const mutation = useApiMutation(
    (data: {
      verdict: VerdictChoice;
      sentence?: string;
      notes?: string;
      trial_date?: string;
    }) => trialsApi.create(suspectId, data),
    {
      successMessage: 'Trial recorded',
      invalidateKeys: [['suspects', suspectId]],
    },
  );

  const displayError = validationError || (mutation.error ? extractErrorMessage(mutation.error) : '');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!verdict) { setValidationError('Verdict is required'); return; }
    setValidationError('');
    mutation.mutate(
      {
        verdict: verdict as VerdictChoice,
        sentence: sentence || undefined,
        notes: notes || undefined,
        trial_date: trialDate || undefined,
      },
      { onSuccess },
    );
  };

  return (
    <form className="trial-form" onSubmit={handleSubmit}>
      <h3>Record Trial Verdict</h3>
      {displayError && <Alert type="error" onClose={() => { setValidationError(''); mutation.reset(); }}>{displayError}</Alert>}

      <Select label="Verdict" required options={VERDICT_OPTIONS} value={verdict} onChange={(e) => setVerdict(e.target.value)} placeholder="Select verdict" />
      {verdict === 'guilty' && (
        <Input label="Sentence" value={sentence} onChange={(e) => setSentence(e.target.value)} placeholder="Punishment description" />
      )}
      <Input label="Trial Date" type="date" value={trialDate} onChange={(e) => setTrialDate(e.target.value)} />
      <Textarea label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
      <Button type="submit" variant="primary" loading={mutation.isPending}>Record Verdict</Button>
    </form>
  );
}
