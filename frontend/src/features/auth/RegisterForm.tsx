/**
 * Register form — mirrors backend RegisterRequestSerializer.
 * Fields: username, password, password_confirm, email, phone_number,
 * first_name, last_name, national_id
 * Validation matches backend: national_id 10 digits, phone Iranian mobile.
 */

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, Link } from 'react-router-dom';
import { register as apiRegister } from '../../services/api/auth.api';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import type { ApiError } from '../../types/api.types';

const iranianMobileRegex = /^(\+98|0)?9\d{9}$/;

const registerSchema = z
  .object({
    username: z.string().min(1, 'Username is required'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    password_confirm: z.string().min(1, 'Please confirm your password'),
    email: z.string().min(1, 'Email is required').email('Invalid email'),
    phone_number: z
      .string()
      .min(1, 'Phone number is required')
      .regex(iranianMobileRegex, 'Phone must be a valid Iranian mobile (e.g. 09121234567)'),
    first_name: z.string().min(1, 'First name is required'),
    last_name: z.string().min(1, 'Last name is required'),
    national_id: z
      .string()
      .length(10, 'National ID must be exactly 10 digits')
      .regex(/^\d+$/, 'National ID must contain only digits'),
  })
  .refine((data) => data.password === data.password_confirm, {
    message: 'Passwords do not match',
    path: ['password_confirm'],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

export const RegisterForm: React.FC = () => {
  const navigate = useNavigate();
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: '',
      password: '',
      password_confirm: '',
      email: '',
      phone_number: '',
      first_name: '',
      last_name: '',
      national_id: '',
    },
  });

  const onSubmit = async (data: RegisterFormData) => {
    setSubmitError(null);
    try {
      await apiRegister({
        username: data.username,
        password: data.password,
        password_confirm: data.password_confirm,
        email: data.email,
        phone_number: data.phone_number,
        first_name: data.first_name,
        last_name: data.last_name,
        national_id: data.national_id,
      });
      navigate('/login', { replace: true });
    } catch (err) {
      const axiosError = err as { response?: { data?: ApiError } };
      const data = axiosError.response?.data;
      if (data?.detail && typeof data.detail === 'string') {
        setSubmitError(data.detail);
      } else if (data && typeof data === 'object') {
        const fieldErrors = Object.entries(data)
          .filter(([, v]) => Array.isArray(v) && v.length > 0)
          .map(([k, v]) => `${k}: ${(v as string[]).join(', ')}`)
          .join('; ');
        setSubmitError(fieldErrors || 'ثبت‌نام ناموفق بود. لطفاً دوباره تلاش کنید.');
      } else {
        setSubmitError('ثبت‌نام ناموفق بود. لطفاً دوباره تلاش کنید.');
      }
    }
  };

  return (
    <Card title="ثبت‌نام">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {submitError && (
          <div className="rounded-lg bg-red-500/20 px-4 py-3 text-right text-sm text-red-400">
            {submitError}
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="نام"
            error={errors.first_name?.message}
            {...register('first_name')}
          />
          <Input
            label="نام خانوادگی"
            error={errors.last_name?.message}
            {...register('last_name')}
          />
        </div>
        <Input
          label="نام کاربری"
          autoComplete="username"
          error={errors.username?.message}
          {...register('username')}
        />
        <Input
          label="ایمیل"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register('email')}
        />
        <Input
          label="شماره ملی (۱۰ رقم)"
          error={errors.national_id?.message}
          {...register('national_id')}
        />
        <Input
          label="شماره تلفن همراه"
          type="tel"
          placeholder="09121234567"
          error={errors.phone_number?.message}
          {...register('phone_number')}
        />
        <Input
          label="رمز عبور"
          type="password"
          autoComplete="new-password"
          error={errors.password?.message}
          {...register('password')}
        />
        <Input
          label="تکرار رمز عبور"
          type="password"
          autoComplete="new-password"
          error={errors.password_confirm?.message}
          {...register('password_confirm')}
        />
        <div className="flex flex-col gap-3 pt-2">
          <Button type="submit" loading={isSubmitting} className="w-full">
            ثبت‌نام
          </Button>
          <p className="text-right text-sm text-slate-400">
            قبلاً ثبت‌نام کرده‌اید؟{' '}
            <Link to="/login" className="text-blue-400 hover:underline">
              ورود
            </Link>
          </p>
        </div>
      </form>
    </Card>
  );
};
