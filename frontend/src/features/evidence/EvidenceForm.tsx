/**
 * EvidenceForm — polymorphic evidence registration form.
 *
 * Common fields: title, description, case.
 * Type-specific fields rendered based on evidence_type selection.
 *
 * Corrections vs original:
 * - Removed phantom collection_date / location (not in backend model)
 * - statement_text required for testimony (backend validates)
 * - vehicle_model / color required for vehicle; XOR on license_plate / serial_number
 * - owner_full_name required for identity; added document_details key-value UI
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
  // Testimony
  const [statementText, setStatementText] = useState('');
  // Vehicle
  const [vehicleModel, setVehicleModel] = useState('');
  const [color, setColor] = useState('');
  const [licensePlate, setLicensePlate] = useState('');
  const [serialNumber, setSerialNumber] = useState('');
  // Identity
  const [ownerFullName, setOwnerFullName] = useState('');
  const [docEntries, setDocEntries] = useState<{ key: string; value: string }[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  /* ── Document details helpers ────────────────────────────────── */
  const addDocEntry = () => setDocEntries((prev) => [...prev, { key: '', value: '' }]);
  const removeDocEntry = (idx: number) => setDocEntries((prev) => prev.filter((_, i) => i !== idx));
  const updateDocEntry = (idx: number, field: 'key' | 'value', val: string) =>
    setDocEntries((prev) => prev.map((e, i) => (i === idx ? { ...e, [field]: val } : e)));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    const errs: Record<string, string> = {};
    if (!title.trim()) errs.title = 'Title is required';
    if (!description.trim()) errs.description = 'Description is required';
    if (!caseField) errs.case = 'Case ID is required';

    // Type-specific validations
    if (evidenceType === 'testimony' && !statementText.trim()) {
      errs.statementText = 'Statement text is required for testimony evidence';
    }
    if (evidenceType === 'vehicle') {
      if (!vehicleModel.trim()) errs.vehicleModel = 'Vehicle model is required';
      if (!color.trim()) errs.color = 'Color is required';
      if (!licensePlate.trim() && !serialNumber.trim()) {
        errs.licensePlate = 'Either license plate or serial number is required';
      }
      if (licensePlate.trim() && serialNumber.trim()) {
        errs.licensePlate = 'Provide either license plate or serial number, not both';
      }
    }
    if (evidenceType === 'identity' && !ownerFullName.trim()) {
      errs.ownerFullName = 'Owner full name is required';
    }

    if (Object.keys(errs).length > 0) { setFieldErrors(errs); return; }

    setLoading(true);
    try {
      const payload: EvidenceCreateRequest = {
        evidence_type: evidenceType as EvidenceType,
        title: title.trim(),
        description: description.trim(),
        case: Number(caseField),
      };

      if (evidenceType === 'testimony') {
        payload.statement_text = statementText.trim();
      } else if (evidenceType === 'vehicle') {
        payload.vehicle_model = vehicleModel.trim();
        payload.color = color.trim();
        payload.license_plate = licensePlate.trim() || undefined;
        payload.serial_number = serialNumber.trim() || undefined;
      } else if (evidenceType === 'identity') {
        payload.owner_full_name = ownerFullName.trim();
        if (docEntries.length > 0) {
          const details: Record<string, string> = {};
          for (const entry of docEntries) {
            if (entry.key.trim()) details[entry.key.trim()] = entry.value.trim();
          }
          if (Object.keys(details).length > 0) payload.document_details = details;
        }
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
      </div>

      {/* ── Type-specific fields ─────────────────────────────────── */}

      {evidenceType === 'testimony' && (
        <Textarea
          label="Statement Text"
          required
          value={statementText}
          onChange={(e) => setStatementText(e.target.value)}
          rows={5}
          placeholder="Witness statement…"
          error={fieldErrors.statementText}
        />
      )}

      {evidenceType === 'vehicle' && (
        <>
          <div className="evidence-form__row">
            <Input label="Vehicle Model" required value={vehicleModel} onChange={(e) => setVehicleModel(e.target.value)} error={fieldErrors.vehicleModel} />
            <Input label="Color" required value={color} onChange={(e) => setColor(e.target.value)} error={fieldErrors.color} />
          </div>
          <div className="evidence-form__row">
            <Input label="License Plate" value={licensePlate} onChange={(e) => setLicensePlate(e.target.value)} error={fieldErrors.licensePlate} placeholder="Either plate or serial…" />
            <Input label="Serial Number" value={serialNumber} onChange={(e) => setSerialNumber(e.target.value)} placeholder="Either serial or plate…" />
          </div>
        </>
      )}

      {evidenceType === 'identity' && (
        <>
          <Input label="Owner Full Name" required value={ownerFullName} onChange={(e) => setOwnerFullName(e.target.value)} error={fieldErrors.ownerFullName} />

          <fieldset className="evidence-form__doc-details">
            <legend>Document Details (key-value pairs)</legend>
            {docEntries.map((entry, idx) => (
              <div key={idx} className="evidence-form__row">
                <Input
                  label="Key"
                  value={entry.key}
                  onChange={(e) => updateDocEntry(idx, 'key', e.target.value)}
                  placeholder="e.g. passport_number"
                />
                <Input
                  label="Value"
                  value={entry.value}
                  onChange={(e) => updateDocEntry(idx, 'value', e.target.value)}
                  placeholder="e.g. AB1234567"
                />
                <Button type="button" variant="danger" onClick={() => removeDocEntry(idx)}>
                  ✕
                </Button>
              </div>
            ))}
            <Button type="button" variant="secondary" onClick={addDocEntry}>
              + Add Detail
            </Button>
          </fieldset>
        </>
      )}

      <Button type="submit" variant="primary" loading={loading}>
        Register Evidence
      </Button>
    </form>
  );
}
