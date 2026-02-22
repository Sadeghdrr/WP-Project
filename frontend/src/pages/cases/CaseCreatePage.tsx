/**
 * Case creation page — complainant workflow.
 * Create complaint case → submit for Cadet review.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CaseForm } from '../../features/cases/CaseForm';
import {
  createComplaintCase,
  submitForReview,
} from '../../services/api/cases.api';
import type { ComplaintCaseCreateRequest } from '../../types/case.types';

export const CaseCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<'create' | 'submit'>('create');
  const [createdCaseId, setCreatedCaseId] = useState<number | null>(null);

  const handleCreate = async (data: ComplaintCaseCreateRequest) => {
    setError(null);
    setIsLoading(true);
    try {
      const caseData = await createComplaintCase(data);
      setCreatedCaseId(caseData.id);
      setStep('submit');
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(
        axiosError.response?.data?.detail ?? 'خطا در ایجاد پرونده. لطفاً دوباره تلاش کنید.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitForReview = async () => {
    if (!createdCaseId) return;
    setError(null);
    setIsLoading(true);
    try {
      await submitForReview(createdCaseId);
      navigate(`/cases/${createdCaseId}`, { replace: true });
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(
        axiosError.response?.data?.detail ?? 'خطا در ارسال برای بررسی. لطفاً دوباره تلاش کنید.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  if (step === 'submit' && createdCaseId) {
    return (
      <div className="mx-auto max-w-md space-y-4">
        <div className="rounded-lg border border-emerald-500/50 bg-emerald-500/20 p-4 text-right">
          <p className="font-medium text-emerald-200">پرونده با موفقیت ایجاد شد.</p>
          <p className="mt-2 text-sm text-slate-300">
            برای ارسال به بررسی کارآموز، روی دکمه زیر کلیک کنید.
          </p>
        </div>
        {error && (
          <div className="rounded-lg bg-red-500/20 p-4 text-right text-red-400">
            {error}
          </div>
        )}
        <div className="flex gap-2">
          <button
            onClick={handleSubmitForReview}
            disabled={isLoading}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'در حال ارسال...' : 'ارسال برای بررسی'}
          </button>
          <button
            onClick={() => navigate(`/cases/${createdCaseId}`)}
            className="rounded-lg border border-slate-600 px-4 py-2 font-medium text-slate-300 hover:bg-slate-800"
          >
            مشاهده پرونده
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 text-right text-2xl font-bold text-slate-100">
        ثبت شکایت جدید
      </h1>
      {error && (
        <div className="mb-4 rounded-lg bg-red-500/20 p-4 text-right text-red-400">
          {error}
        </div>
      )}
      <CaseForm onSubmit={handleCreate} isLoading={isLoading} />
    </div>
  );
};
