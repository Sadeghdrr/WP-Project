/**
 * Crime scene registration page.
 * Accessible only to police ranks (excluding Cadet).
 * If Police Chief → case opens immediately (no approval).
 * Otherwise → PENDING_APPROVAL, needs superior approval.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CrimeSceneForm } from '../../features/cases/CrimeSceneForm';
import { createCrimeSceneCase } from '../../services/api/cases.api';
import { useAuth } from '../../hooks/useAuth';
import type { CrimeSceneCaseCreateRequest } from '../../types/case.types';

const CADET_ROLE = 'Cadet';
const COMPLAINANT_ROLE = 'Complainant';
const BASE_USER_ROLE = 'Base User';

/** Police roles that can register crime scenes (from setup_rbac — have ADD_CASE, exclude Cadet) */
const CRIME_SCENE_CREATOR_ROLES = [
  'System Admin',
  'Police Chief',
  'Captain',
  'Police Officer',
  'Patrol Officer',
];

export const CrimeSceneCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const roleName = user?.role_detail?.name ?? '';
  const canCreateCrimeScene =
    CRIME_SCENE_CREATOR_ROLES.includes(roleName) &&
    ![CADET_ROLE, COMPLAINANT_ROLE, BASE_USER_ROLE].includes(roleName);

  const isPoliceChief = roleName === 'Police Chief';

  const handleSubmit = async (data: CrimeSceneCaseCreateRequest) => {
    setError(null);
    setIsLoading(true);
    try {
      const caseData = await createCrimeSceneCase(data);
      if (isPoliceChief) {
        // Case is OPEN immediately — no approval needed
        navigate(`/cases/${caseData.id}`, { replace: true });
      } else {
        // Case is PENDING_APPROVAL — show success message
        navigate(`/cases/${caseData.id}`, {
          replace: true,
          state: { message: 'پرونده ثبت شد و در انتظار تأیید مافوق است.' },
        });
      }
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(
        axiosError.response?.data?.detail ?? 'خطا در ثبت پرونده. لطفاً دوباره تلاش کنید.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (!canCreateCrimeScene) {
    return (
      <div className="rounded-lg border border-red-500/50 bg-red-500/20 p-6 text-right">
        <p className="font-medium text-red-200">
          شما دسترسی به ثبت صحنه جرم ندارید.
        </p>
        <p className="mt-2 text-sm text-slate-400">
          فقط درجات پلیس (به‌جز کارآموز) می‌توانند صحنه جرم ثبت کنند.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-right text-2xl font-bold text-slate-100">
        ثبت صحنه جرم
      </h1>
      {isPoliceChief && (
        <div className="mb-4 rounded-lg border border-emerald-500/50 bg-emerald-500/20 p-3 text-right text-sm text-emerald-200">
          با توجه به درجه شما، پرونده بلافاصله پس از ثبت باز می‌شود و نیازی به
          تأیید مافوق ندارد.
        </div>
      )}
      {!isPoliceChief && (
        <div className="mb-4 rounded-lg border border-amber-500/50 bg-amber-500/20 p-3 text-right text-sm text-amber-200">
          پرونده پس از ثبت در انتظار تأیید یک مافوق قرار می‌گیرد.
        </div>
      )}
      {error && (
        <div className="mb-4 rounded-lg bg-red-500/20 p-4 text-right text-red-400">
          {error}
        </div>
      )}
      <CrimeSceneForm onSubmit={handleSubmit} isLoading={isLoading} />
    </div>
  );
};
