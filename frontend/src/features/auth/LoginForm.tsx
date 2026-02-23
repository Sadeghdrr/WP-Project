/**
 * Login form — mirrors backend LoginRequestSerializer.
 * identifier: username | national_id | phone_number | email
 */

import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Input } from '../../components/ui/Input';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import type { ApiError } from '../../types/api.types';

const loginSchema = z.object({
  identifier: z.string().min(1, 'Identifier is required'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginForm: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { identifier: '', password: '' },
  });

  const onSubmit = async (data: LoginFormData) => {
    setSubmitError(null);
    try {
      await login(data);
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? '/dashboard';
      navigate(from, { replace: true });
    } catch (err) {
      const axiosError = err as { response?: { data?: ApiError } };
      const detail = axiosError.response?.data?.detail;
      if (typeof detail === 'string') {
        setSubmitError(detail);
      } else if (Array.isArray(detail)) {
        setSubmitError(detail.join(' '));
      } else {
        setSubmitError('ورود ناموفق بود. لطفاً دوباره تلاش کنید.');
      }
    }
  };

  return (
    <Card title="ورود به سیستم">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {submitError && (
          <div className="rounded-lg bg-red-500/20 px-4 py-3 text-right text-sm text-red-400">
            {submitError}
          </div>
        )}
        <Input
          label="نام کاربری / ایمیل / شماره ملی / شماره تلفن"
          type="text"
          autoComplete="username"
          error={errors.identifier?.message}
          {...register('identifier')}
        />
        <Input
          label="رمز عبور"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register('password')}
        />
        <div className="flex flex-col gap-3 pt-2">
          <Button type="submit" loading={isSubmitting} className="w-full">
            ورود
          </Button>
          <p className="text-right text-sm text-slate-400">
            حساب کاربری ندارید؟{' '}
            <Link to="/register" className="text-blue-400 hover:underline">
              ثبت‌نام
            </Link>
          </p>
        </div>
      </form>
    </Card>
  );
};
