/**
 * WitnessManager — list and add witnesses on a case (crime-scene flow, §4.2.2).
 *
 * Witnesses are NOT system users; they are external persons identified
 * by full name, phone number, and national ID.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Alert } from '@/components/ui/Alert';
import { Skeleton } from '@/components/ui/Skeleton';
import { casesApi } from '@/services/api/cases.api';
import { extractErrorMessage } from '@/utils/errors';

interface WitnessManagerProps {
  caseId: number;
  /** Hide the "add" form (e.g. for closed/voided cases). */
  readOnly?: boolean;
}

export function WitnessManager({ caseId, readOnly = false }: WitnessManagerProps) {
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [nationalId, setNationalId] = useState('');
  const [error, setError] = useState('');

  const { data: witnesses, isLoading } = useQuery({
    queryKey: ['cases', caseId, 'witnesses'],
    queryFn: () => casesApi.witnesses(caseId),
  });

  const addMutation = useMutation({
    mutationFn: () =>
      casesApi.addWitness(caseId, {
        full_name: fullName.trim(),
        phone_number: phoneNumber.trim(),
        national_id: nationalId.trim(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', caseId, 'witnesses'] });
      queryClient.invalidateQueries({ queryKey: ['cases', caseId] });
      setFullName('');
      setPhoneNumber('');
      setNationalId('');
      setError('');
    },
    onError: (err) => setError(extractErrorMessage(err)),
  });

  const canAdd = fullName.trim() && phoneNumber.trim() && nationalId.trim();

  if (isLoading) return <Skeleton height={120} />;

  return (
    <Card>
      <h3>Witnesses</h3>

      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      {witnesses && witnesses.length > 0 ? (
        <ul className="witness-list">
          {witnesses.map((w) => (
            <li key={w.id} className="witness-list__item">
              <span>{w.full_name}</span>
              <span>{w.national_id}</span>
              <span>{w.phone_number}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-muted">No witnesses recorded.</p>
      )}

      {/* Add witness form */}
      {!readOnly && (
        <div className="witness-manager__add">
          <div className="case-form__row">
            <Input
              label="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Witness name"
              size="sm"
            />
            <Input
              label="Phone Number"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+1234567890"
              size="sm"
            />
            <Input
              label="National ID"
              value={nationalId}
              onChange={(e) => setNationalId(e.target.value)}
              placeholder="10-digit ID"
              size="sm"
            />
          </div>
          <Button
            size="sm"
            variant="secondary"
            loading={addMutation.isPending}
            disabled={!canAdd}
            onClick={() => addMutation.mutate()}
          >
            + Add Witness
          </Button>
        </div>
      )}
    </Card>
  );
}
