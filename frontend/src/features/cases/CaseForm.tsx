/**
 * Case creation form — complaint workflow.
 * Mirrors backend ComplaintCaseCreateSerializer.
 */

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { CRIME_LEVEL_LABELS } from '../../config/constants';
import type { ComplaintCaseCreateRequest, CrimeLevelValue } from '../../types/case.types';

const caseCreateSchema = z.object({
  title: z.string().min(1, 'عنوان الزامی است'),
  description: z.string().min(1, 'توضیحات الزامی است'),
  crime_level: z.number().min(1).max(4),
  incident_date: z.string().optional(),
  location: z.string().optional(),
});

type CaseFormData = z.infer<typeof caseCreateSchema>;

export interface CaseFormProps {
  onSubmit: (data: ComplaintCaseCreateRequest) => void | Promise<void>;
  isLoading?: boolean;
  initialValues?: Partial<ComplaintCaseCreateRequest>;
}

export const CaseForm: React.FC<CaseFormProps> = ({
  onSubmit,
  isLoading = false,
  initialValues,
}) => {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CaseFormData>({
    resolver: zodResolver(caseCreateSchema),
    defaultValues: {
      title: initialValues?.title ?? '',
      description: initialValues?.description ?? '',
      crime_level: (initialValues?.crime_level ?? 1) as CrimeLevelValue,
      incident_date: initialValues?.incident_date ?? undefined,
      location: initialValues?.location ?? '',
    },
  });

  const handleFormSubmit = (data: CaseFormData) => {
    const payload: ComplaintCaseCreateRequest = {
      title: data.title,
      description: data.description,
      crime_level: data.crime_level as CrimeLevelValue,
      incident_date: data.incident_date ? new Date(data.incident_date).toISOString() : null,
      location: data.location ?? '',
    };
    onSubmit(payload);
  };

  return (
    <Card title="ثبت شکایت">
      <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
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
            placeholder="جزئیات شکایت را شرح دهید..."
            {...register('description')}
          />
          {errors.description && (
            <p className="mt-1 text-right text-sm text-red-400">
              {errors.description.message}
            </p>
          )}
        </div>
        <div>
          <label className="mb-1 block text-right text-sm font-medium text-slate-300">
            سطح جرم
          </label>
          <select
            className={`w-full rounded-lg border bg-slate-800/50 px-3 py-2 text-right text-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 ${
              errors.crime_level ? 'border-red-500' : 'border-slate-600'
            }`}
            {...register('crime_level', { valueAsNumber: true })}
          >
            {Object.entries(CRIME_LEVEL_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          {errors.crime_level && (
            <p className="mt-1 text-right text-sm text-red-400">
              {errors.crime_level.message}
            </p>
          )}
        </div>
        <Input
          label="تاریخ و زمان حادثه"
          type="datetime-local"
          error={errors.incident_date?.message}
          {...register('incident_date')}
        />
        <Input
          label="محل حادثه"
          error={errors.location?.message}
          {...register('location')}
        />
        <Button type="submit" loading={isLoading} className="w-full">
          ایجاد پرونده
        </Button>
      </form>
    </Card>
  );
};
