/**
 * BountyTipPage — submit bounty tips and look up rewards.
 */
import { useState } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { Card } from '@/components/ui/Card';
import { BountyTipForm } from '@/features/suspects/BountyTipForm';
import { bountyTipsApi } from '@/services/api/suspects.api';
import { extractErrorMessage } from '@/utils/errors';

export function BountyTipPage() {
  const [nationalId, setNationalId] = useState('');
  const [uniqueCode, setUniqueCode] = useState('');
  const [reward, setReward] = useState<Record<string, unknown> | null>(null);
  const [lookupError, setLookupError] = useState('');
  const [lookupLoading, setLookupLoading] = useState(false);

  const handleLookup = async () => {
    if (!nationalId || !uniqueCode) { setLookupError('Both fields are required'); return; }
    setLookupError('');
    setLookupLoading(true);
    try {
      const result = await bountyTipsApi.lookupReward({ national_id: nationalId, unique_code: uniqueCode });
      setReward(result);
    } catch (err) {
      setLookupError(extractErrorMessage(err));
      setReward(null);
    } finally {
      setLookupLoading(false);
    }
  };

  return (
    <div className="page-bounty-tip">
      <div className="page-header">
        <h1 className="page-header__title">Bounty Tips</h1>
      </div>

      <BountyTipForm />

      {/* Reward lookup */}
      <Card className="bounty-lookup">
        <h3>Look Up Your Reward</h3>
        {lookupError && <Alert type="error" onClose={() => setLookupError('')}>{lookupError}</Alert>}

        <div className="bounty-lookup__row">
          <Input label="National ID" value={nationalId} onChange={(e) => setNationalId(e.target.value)} placeholder="Enter your national ID" />
          <Input label="Unique Code" value={uniqueCode} onChange={(e) => setUniqueCode(e.target.value)} placeholder="Code from your tip receipt" />
        </div>
        <Button variant="secondary" loading={lookupLoading} onClick={handleLookup}>Look Up</Button>

        {reward && (
          <div className="bounty-lookup__result">
            <pre>{JSON.stringify(reward, null, 2) as string}</pre>
          </div>
        )}
      </Card>
    </div>
  );
}
