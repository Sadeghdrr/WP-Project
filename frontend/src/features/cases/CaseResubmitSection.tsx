/**
 * Resubmit section — complainant edits and re-submits returned case.
 * Calls POST /api/cases/{id}/resubmit/ with ResubmitComplaintSerializer.
 */

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { resubmitComplaint } from '../../services/api/cases.api';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import type { Case, ResubmitComplaintRequest } from '../../types/case.types';

const resubmitSchema = z.object({
  title: z.string().min(1, 'عنوان الزامی است'),
  description: z.string().min(1, 'توضیحات الزامی است'),
  incident_date: z.string().optional(),
  location: z.string().optional(),
});

type ResubmitFormData = z.infer<typeof resubmitSchema>;

export interface CaseResubmitSectionProps {
  caseData: Case;
  onResubmit: () => void;
  isLoading: boolean;
  setLoading: (v: boolean) => void;
  setError: (v: string | null) => void;
}

export const CaseResubmitSection: React.FC<CaseResubmitSectionProps> = ({
  caseData,
  onResubmit,
  isLoading,
  setLoading,
  setError,
}) => {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResubmitFormData>({
    resolver: zodResolver(resubmitSchema),
    defaultValues: {
      title: caseData.title,
      description: caseData.description,
      incident_date: caseData.incident_date
        ? caseData.incident_date.slice(0, 16)
        : undefined,
      location: caseData.location ?? '',
    },
  });

  const onSubmit = async (data: ResubmitFormData) => {
    setError(null);
    setLoading(true);
    try {
      const payload: ResubmitComplaintRequest = {
        title: data.title,
        description: data.description,
        incident_date: data.incident_date
          ? new Date(data.incident_date).toISOString()
          : null,
        location: data.location ?? '',
      };
      await resubmitComplaint(caseData.id, payload);
      onResubmit();
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(
        axiosError.response?.data?.detail ?? 'خطا در ارسال مجدد. لطفاً دوباره تلاش کنید.'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="ویرایش و ارسال مجدد">
      <p className="mb-4 text-right text-sm text-slate-400">
        پرونده به شما برگردانده شده است. پس از ویرایش، دوباره ارسال کنید.
      </p>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="عنوان پرونده"
          error={errors.title?.message}
          {...register('title')}
        />
        <div>
          <label className="mb-1 block text-right text-sm font-medium text-slate-300">
            توضیحات
          </label>
          <textarea
            className={`w-full rounded-lg border bg-slate-800/50 px-3 py-2 text-right text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 ${
              errors.description ? 'border-red-500' : 'border-slate-600'
            }`}
            rows={5}
            {...register('description')}
          />
          {errors.description && (
            <p className="mt-1 text-right text-sm text-red-400">
              {errors.description.message}
            </p>
          )}
        </div>
        <Input
          label="تاریخ و زمان حادثه"
          type="datetime-local"
          {...register('incident_date')}
        />
        <Input label="محل حادثه" {...register('location')} />
        <Button type="submit" loading={isLoading}>
          ارسال مجدد برای بررسی
        </Button>
      </form>
    </Card>
  );
};
