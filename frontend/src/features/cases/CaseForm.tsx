/**
 * CaseForm — creates a new case (complaint or crime-scene workflow).
 *
 * Complaint: title*, description*, crime_level*, incident_date, location.
 * Crime Scene: title*, description*, crime_level*, incident_date*, location*, witnesses[].
 */
import { useState, type FormEvent } from 'react';
import { Input, Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { Card } from '@/components/ui/Card';
import { casesApi } from '@/services/api/cases.api';
import { extractErrorMessage } from '@/utils/errors';
import type { CaseDetail, CaseCreateRequest, CaseCreationType, CrimeLevel, WitnessCreateRequest } from '@/types/case.types';

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

const EMPTY_WITNESS: WitnessCreateRequest = { full_name: '', phone_number: '', national_id: '' };

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
  const [witnesses, setWitnesses] = useState<WitnessCreateRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const isCrimeScene = creationType === 'crime_scene';

  const addWitness = () => setWitnesses((prev) => [...prev, { ...EMPTY_WITNESS }]);

  const removeWitness = (idx: number) =>
    setWitnesses((prev) => prev.filter((_, i) => i !== idx));

  const updateWitness = (idx: number, field: keyof WitnessCreateRequest, value: string) =>
    setWitnesses((prev) =>
      prev.map((w, i) => (i === idx ? { ...w, [field]: value } : w)),
    );

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    // Client-side validation
    const errs: Record<string, string> = {};
    if (!title.trim()) errs.title = 'Title is required';
    if (!description.trim()) errs.description = 'Description is required';
    if (!crimeLevel) errs.crime_level = 'Crime level is required';

    if (isCrimeScene) {
      if (!incidentDate) errs.incident_date = 'Incident date is required for crime scene cases';
      if (!location.trim()) errs.location = 'Location is required for crime scene cases';
    }

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

      if (isCrimeScene && witnesses.length > 0) {
        payload.witnesses = witnesses.filter(
          (w) => w.full_name.trim() && w.phone_number.trim() && w.national_id.trim(),
        );
      }

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
          onChange={(e) => {
            setCreationType(e.target.value);
            if (e.target.value !== 'crime_scene') setWitnesses([]);
          }}
        />
      </div>

      <div className="case-form__row">
        <Input
          label="Incident Date"
          type="date"
          required={isCrimeScene}
          value={incidentDate}
          onChange={(e) => setIncidentDate(e.target.value)}
          error={fieldErrors.incident_date}
        />

        <Input
          label="Location"
          required={isCrimeScene}
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          error={fieldErrors.location}
          placeholder="e.g. 123 Main St"
        />
      </div>

      {/* Witnesses — crime-scene only (§4.2.2) */}
      {isCrimeScene && (
        <Card>
          <div className="case-form__witnesses-header">
            <h3>Witnesses</h3>
            <Button type="button" size="sm" variant="secondary" onClick={addWitness}>
              + Add Witness
            </Button>
          </div>

          {witnesses.length === 0 && (
            <p className="text-muted">No witnesses added. Click &quot;+ Add Witness&quot; to record witness details.</p>
          )}

          {witnesses.map((w, idx) => (
            <div key={idx} className="case-form__witness-row">
              <Input
                label="Full Name"
                required
                value={w.full_name}
                onChange={(e) => updateWitness(idx, 'full_name', e.target.value)}
                placeholder="Witness full name"
                size="sm"
              />
              <Input
                label="Phone Number"
                required
                value={w.phone_number}
                onChange={(e) => updateWitness(idx, 'phone_number', e.target.value)}
                placeholder="+1234567890"
                size="sm"
              />
              <Input
                label="National ID"
                required
                value={w.national_id}
                onChange={(e) => updateWitness(idx, 'national_id', e.target.value)}
                placeholder="10-digit ID"
                size="sm"
              />
              <Button
                type="button"
                size="sm"
                variant="danger"
                onClick={() => removeWitness(idx)}
              >
                Remove
              </Button>
            </div>
          ))}
        </Card>
      )}

      <Button type="submit" variant="primary" loading={loading}>
        Create Case
      </Button>
    </form>
  );
}
