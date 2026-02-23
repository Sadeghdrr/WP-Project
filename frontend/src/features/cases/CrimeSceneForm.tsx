/**
 * Crime scene case creation form.
 * Mirrors backend CrimeSceneCaseCreateSerializer.
 * Required: title, description, crime_level, incident_date, location.
 * Optional: witnesses (full_name, phone_number, national_id).
 */

import React, { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { CRIME_LEVEL_LABELS } from '../../config/constants';
import type {
  CrimeSceneCaseCreateRequest,
  WitnessCreateRequest,
  CrimeLevelValue,
} from '../../types/case.types';

const iranianMobileRegex = /^(\+98|0)?9\d{9}$/;

const witnessSchema = z.object({
  full_name: z.string().min(1, 'نام کامل الزامی است'),
  phone_number: z
    .string()
    .min(1, 'شماره تلفن الزامی است')
    .regex(iranianMobileRegex, 'شماره موبایل معتبر وارد کنید (مثال: 09121234567)'),
  national_id: z
    .string()
    .length(10, 'شماره ملی باید ۱۰ رقم باشد')
    .regex(/^\d+$/, 'فقط اعداد'),
});

const crimeSceneSchema = z.object({
  title: z.string().min(1, 'عنوان الزامی است'),
  description: z.string().min(1, 'توضیحات الزامی است'),
  crime_level: z.number().min(1).max(4),
  incident_date: z.string().min(1, 'تاریخ و زمان حادثه الزامی است'),
  location: z.string().min(1, 'محل حادثه الزامی است'),
  witnesses: z.array(witnessSchema).optional(),
});

type CrimeSceneFormData = z.infer<typeof crimeSceneSchema>;

export interface CrimeSceneFormProps {
  onSubmit: (data: CrimeSceneCaseCreateRequest) => void | Promise<void>;
  isLoading?: boolean;
}

export const CrimeSceneForm: React.FC<CrimeSceneFormProps> = ({
  onSubmit,
  isLoading = false,
}) => {
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<CrimeSceneFormData>({
    resolver: zodResolver(crimeSceneSchema),
    defaultValues: {
      title: '',
      description: '',
      crime_level: 1,
      incident_date: '',
      location: '',
      witnesses: [],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'witnesses',
  });

  const handleFormSubmit = (data: CrimeSceneFormData) => {
    const payload: CrimeSceneCaseCreateRequest = {
      title: data.title,
      description: data.description,
      crime_level: data.crime_level as CrimeLevelValue,
      incident_date: new Date(data.incident_date).toISOString(),
      location: data.location,
      witnesses:
        data.witnesses && data.witnesses.length > 0
          ? (data.witnesses as WitnessCreateRequest[])
          : undefined,
    };
    onSubmit(payload);
  };

  return (
    <Card title="ثبت صحنه جرم">
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
            placeholder="جزئیات صحنه جرم را شرح دهید..."
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
        </div>
        <Input
          label="تاریخ و زمان حادثه"
          type="datetime-local"
          required
          error={errors.incident_date?.message}
          {...register('incident_date')}
        />
        <Input
          label="محل حادثه"
          required
          error={errors.location?.message}
          {...register('location')}
        />

        <div className="space-y-4 border-t border-slate-700 pt-4">
          <div className="flex flex-row-reverse items-center justify-between">
            <h3 className="font-medium text-slate-200">شاهدان</h3>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => append({ full_name: '', phone_number: '', national_id: '' })}
            >
              افزودن شاهد
            </Button>
          </div>
          {fields.length === 0 ? (
            <p className="text-right text-sm text-slate-500">
              هنوز شاهی ثبت نشده است. (اختیاری)
            </p>
          ) : (
            <div className="space-y-3">
              {fields.map((field, index) => (
                <div
                  key={field.id}
                  className="rounded-lg border border-slate-700 bg-slate-800/30 p-4"
                >
                  <div className="mb-3 flex flex-row-reverse justify-between">
                    <span className="text-sm font-medium text-slate-400">
                      شاهد {index + 1}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => remove(index)}
                    >
                      حذف
                    </Button>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <Input
                      label="نام کامل"
                      error={errors.witnesses?.[index]?.full_name?.message}
                      {...register(`witnesses.${index}.full_name`)}
                    />
                    <Input
                      label="شماره تلفن"
                      placeholder="09121234567"
                      error={errors.witnesses?.[index]?.phone_number?.message}
                      {...register(`witnesses.${index}.phone_number`)}
                    />
                    <Input
                      label="شماره ملی (۱۰ رقم)"
                      error={errors.witnesses?.[index]?.national_id?.message}
                      {...register(`witnesses.${index}.national_id`)}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <Button type="submit" loading={isLoading} className="w-full">
          ثبت پرونده
        </Button>
      </form>
    </Card>
  );
};
