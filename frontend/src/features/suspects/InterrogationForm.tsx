/**
 * InterrogationForm — record an interrogation.
 */
import { useState, type FormEvent } from 'react';
import { Input, Textarea } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { interrogationsApi } from '@/services/api/suspects.api';
import { extractErrorMessage } from '@/utils/errors';
import { useToast } from '@/context/ToastContext';

interface InterrogationFormProps {
  suspectId: number;
  onSuccess: () => void;
}

export function InterrogationForm({ suspectId, onSuccess }: InterrogationFormProps) {
  const toast = useToast();
  const [technique, setTechnique] = useState('');
  const [questions, setQuestions] = useState('');
  const [responses, setResponses] = useState('');
  const [score, setScore] = useState('');
  const [notes, setNotes] = useState('');
  const [duration, setDuration] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!score || Number(score) < 1 || Number(score) > 10) {
      setError('Guilt score must be between 1 and 10');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await interrogationsApi.create(suspectId, {
        technique: technique || undefined,
        questions: questions || undefined,
        responses: responses || undefined,
        score: Number(score),
        notes: notes || undefined,
        duration_minutes: duration ? Number(duration) : undefined,
      });
      toast.success('Interrogation recorded');
      onSuccess();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="interrogation-form" onSubmit={handleSubmit}>
      <h3>Record Interrogation</h3>
      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      <Input label="Technique" value={technique} onChange={(e) => setTechnique(e.target.value)} placeholder="e.g. Standard, Reid" />
      <Textarea label="Questions" value={questions} onChange={(e) => setQuestions(e.target.value)} rows={3} />
      <Textarea label="Responses" value={responses} onChange={(e) => setResponses(e.target.value)} rows={3} />
      <div className="interrogation-form__row">
        <Input label="Guilt Score (1–10)" required type="number" min={1} max={10} value={score} onChange={(e) => setScore(e.target.value)} />
        <Input label="Duration (min)" type="number" value={duration} onChange={(e) => setDuration(e.target.value)} />
      </div>
      <Textarea label="Notes" value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
      <Button type="submit" variant="primary" loading={loading}>Submit Interrogation</Button>
    </form>
  );
}
