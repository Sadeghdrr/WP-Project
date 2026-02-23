/**
 * EvidenceForm — polymorphic evidence registration form.
 *
 * Shows common fields (title, description, case, collection_date, location)
 * plus type-specific fields based on the selected evidence_type.
 */
import { useState, type FormEvent } from 'react';
import { Input, Textarea } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { evidenceApi } from '@/services/api/evidence.api';
import { extractErrorMessage } from '@/utils/errors';
import type { EvidenceDetail, EvidenceCreateRequest, EvidenceType } from '@/types/evidence.types';

const TYPE_OPTIONS = [
  { value: 'testimony', label: 'Testimony' },
  { value: 'biological', label: 'Biological' },
  { value: 'vehicle', label: 'Vehicle' },
  { value: 'identity', label: 'Identity' },
  { value: 'other', label: 'Other' },
];

interface EvidenceFormProps {
  caseId?: number;
  onSuccess?: (created: EvidenceDetail) => void;
}

export function EvidenceForm({ caseId, onSuccess }: EvidenceFormProps) {
  const [evidenceType, setEvidenceType] = useState<string>('testimony');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [caseField, setCaseField] = useState(caseId?.toString() ?? '');
  const [collectionDate, setCollectionDate] = useState('');
  const [location, setLocation] = useState('');
  // Testimony
  const [statementText, setStatementText] = useState('');
  // Vehicle
  const [vehicleModel, setVehicleModel] = useState('');
  const [color, setColor] = useState('');
  const [licensePlate, setLicensePlate] = useState('');
  const [serialNumber, setSerialNumber] = useState('');
  // Identity
  const [ownerFullName, setOwnerFullName] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    const errs: Record<string, string> = {};
    if (!title.trim()) errs.title = 'Title is required';
    if (!description.trim()) errs.description = 'Description is required';
    if (!caseField) errs.case = 'Case ID is required';
    if (Object.keys(errs).length > 0) { setFieldErrors(errs); return; }

    setLoading(true);
    try {
      const payload: EvidenceCreateRequest = {
        evidence_type: evidenceType as EvidenceType,
        title: title.trim(),
        description: description.trim(),
        case: Number(caseField),
        collection_date: collectionDate || undefined,
        location: location.trim() || undefined,
      };

      if (evidenceType === 'testimony') {
        payload.statement_text = statementText;
      } else if (evidenceType === 'vehicle') {
        payload.vehicle_model = vehicleModel || undefined;
        payload.color = color || undefined;
        payload.license_plate = licensePlate || undefined;
        payload.serial_number = serialNumber || undefined;
      } else if (evidenceType === 'identity') {
        payload.owner_full_name = ownerFullName || undefined;
      }

      const created = await evidenceApi.create(payload);
      onSuccess?.(created);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="evidence-form" onSubmit={handleSubmit}>
      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      <Select
        label="Evidence Type"
        required
        options={TYPE_OPTIONS}
        value={evidenceType}
        onChange={(e) => setEvidenceType(e.target.value)}
      />

      <Input label="Title" required value={title} onChange={(e) => setTitle(e.target.value)} error={fieldErrors.title} />
      <Textarea label="Description" required value={description} onChange={(e) => setDescription(e.target.value)} error={fieldErrors.description} rows={3} />

      <div className="evidence-form__row">
        <Input label="Case ID" required type="number" value={caseField} onChange={(e) => setCaseField(e.target.value)} error={fieldErrors.case} disabled={!!caseId} />
        <Input label="Collection Date" type="date" value={collectionDate} onChange={(e) => setCollectionDate(e.target.value)} />
        <Input label="Location" value={location} onChange={(e) => setLocation(e.target.value)} />
      </div>

      {/* Type-specific fields */}
      {evidenceType === 'testimony' && (
        <Textarea label="Statement Text" value={statementText} onChange={(e) => setStatementText(e.target.value)} rows={5} placeholder="Witness statement…" />
      )}

      {evidenceType === 'vehicle' && (
        <div className="evidence-form__row">
          <Input label="Vehicle Model" value={vehicleModel} onChange={(e) => setVehicleModel(e.target.value)} />
          <Input label="Color" value={color} onChange={(e) => setColor(e.target.value)} />
          <Input label="License Plate" value={licensePlate} onChange={(e) => setLicensePlate(e.target.value)} />
          <Input label="Serial Number" value={serialNumber} onChange={(e) => setSerialNumber(e.target.value)} />
        </div>
      )}

      {evidenceType === 'identity' && (
        <Input label="Owner Full Name" value={ownerFullName} onChange={(e) => setOwnerFullName(e.target.value)} />
      )}

      <Button type="submit" variant="primary" loading={loading}>
        Register Evidence
      </Button>
    </form>
  );
}
