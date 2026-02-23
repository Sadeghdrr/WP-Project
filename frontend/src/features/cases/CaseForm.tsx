/**
 * CaseForm — creates a new case (complaint or crime-scene workflow).
 *
 * Fields: title*, description*, crime_level*, creation_type, incident_date, location.
 */
import { useState, type FormEvent } from 'react';
import { Input, Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { casesApi } from '@/services/api/cases.api';
import { extractErrorMessage } from '@/utils/errors';
import type { CaseDetail, CaseCreateRequest, CaseCreationType, CrimeLevel } from '@/types/case.types';

const CRIME_LEVEL_OPTIONS = [
  { value: '1', label: 'Level 3 (Minor)' },
  { value: '2', label: 'Level 2 (Moderate)' },
  { value: '3', label: 'Level 1 (Serious)' },
  { value: '4', label: 'Critical' },
];

const CREATION_TYPE_OPTIONS = [
  { value: 'complaint', label: 'Complaint' },
  { value: 'crime_scene', label: 'Crime Scene' },
];

interface CaseFormProps {
  onSuccess?: (created: CaseDetail) => void;
}

export function CaseForm({ onSuccess }: CaseFormProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [crimeLevel, setCrimeLevel] = useState('');
  const [creationType, setCreationType] = useState<string>('complaint');
  const [incidentDate, setIncidentDate] = useState('');
  const [location, setLocation] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    // Client-side validation
    const errs: Record<string, string> = {};
    if (!title.trim()) errs.title = 'Title is required';
    if (!description.trim()) errs.description = 'Description is required';
    if (!crimeLevel) errs.crime_level = 'Crime level is required';

    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      return;
    }

    setLoading(true);
    try {
      const payload: CaseCreateRequest = {
        title: title.trim(),
        description: description.trim(),
        crime_level: Number(crimeLevel) as CrimeLevel,
        creation_type: creationType as CaseCreationType,
        incident_date: incidentDate || undefined,
        location: location.trim() || undefined,
      };
      const created = await casesApi.create(payload);
      onSuccess?.(created);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="case-form" onSubmit={handleSubmit}>
      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      <Input
        label="Title"
        required
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        error={fieldErrors.title}
        placeholder="Brief case title"
      />

      <Textarea
        label="Description"
        required
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        error={fieldErrors.description}
        placeholder="Full description of the incident"
        rows={4}
      />

      <div className="case-form__row">
        <Select
          label="Crime Level"
          required
          options={CRIME_LEVEL_OPTIONS}
          value={crimeLevel}
          onChange={(e) => setCrimeLevel(e.target.value)}
          error={fieldErrors.crime_level}
          placeholder="Select level"
        />

        <Select
          label="Creation Type"
          options={CREATION_TYPE_OPTIONS}
          value={creationType}
          onChange={(e) => setCreationType(e.target.value)}
        />
      </div>

      <div className="case-form__row">
        <Input
          label="Incident Date"
          type="date"
          value={incidentDate}
          onChange={(e) => setIncidentDate(e.target.value)}
        />

        <Input
          label="Location"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="e.g. 123 Main St"
        />
      </div>

      <Button type="submit" variant="primary" loading={loading}>
        Create Case
      </Button>
    </form>
  );
}
