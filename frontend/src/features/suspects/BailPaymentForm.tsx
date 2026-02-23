/**
 * BailPaymentForm — displays bail details and allows payment initiation.
 */
import { useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { Card } from '@/components/ui/Card';
import { bailsApi } from '@/services/api/suspects.api';
import { extractErrorMessage } from '@/utils/errors';
import { useToast } from '@/context/ToastContext';
import type { BailListItem } from '@/types/suspect.types';

interface BailPaymentFormProps {
  suspectId: number;
  bails: BailListItem[];
  onPaymentComplete: () => void;
}

export function BailPaymentForm({ suspectId, bails, onPaymentComplete }: BailPaymentFormProps) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handlePay = async (bailId: number) => {
    setError('');
    setLoading(true);
    try {
      await bailsApi.pay(suspectId, bailId);
      toast.success('Payment processed successfully');
      onPaymentComplete();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (bails.length === 0) return null;

  return (
    <div className="bail-payment">
      <h3>Bail Information</h3>
      {error && <Alert type="error" onClose={() => setError('')}>{error}</Alert>}

      {bails.map((bail) => (
        <Card key={bail.id} className="bail-payment__card">
          <div className="bail-payment__info">
            <p><strong>Amount:</strong> {bail.amount.toLocaleString()} Rials</p>
            <p><strong>Conditions:</strong> {bail.conditions || '—'}</p>
            <Badge variant={bail.is_paid ? 'success' : 'warning'}>
              {bail.is_paid ? 'Paid' : 'Unpaid'}
            </Badge>
            {bail.paid_at && <p><strong>Paid at:</strong> {new Date(bail.paid_at).toLocaleString()}</p>}
          </div>
          {!bail.is_paid && (
            <Button variant="primary" loading={loading} onClick={() => handlePay(bail.id)}>
              Pay Bail
            </Button>
          )}
        </Card>
      ))}
    </div>
  );
}
