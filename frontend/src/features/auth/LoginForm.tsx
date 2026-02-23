/**
 * LoginForm — authentication form supporting identifier + password.
 *
 * The `identifier` field accepts any of: username, email, phone number,
 * or national ID.  Delegates to AuthContext.login() which calls
 * POST /accounts/auth/login/.
 */
import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/context/ToastContext';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { extractErrorMessage, extractFieldErrors } from '@/utils/errors';

export const LoginForm: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? '/dashboard';

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setFieldErrors({});

    // Client-side validation
    if (!identifier.trim()) {
      setFieldErrors({ identifier: 'Please enter your username, email, phone, or national ID' });
      return;
    }
    if (!password) {
      setFieldErrors({ password: 'Please enter your password' });
      return;
    }

    setLoading(true);
    try {
      await login({ identifier: identifier.trim(), password });
      toast.success('Welcome back!');
      navigate(from, { replace: true });
    } catch (err) {
      const fe = extractFieldErrors(err);
      if (fe) {
        setFieldErrors(fe);
      }
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <div className="auth-form__header">
        <h1 className="auth-form__title">Sign In</h1>
        <p className="auth-form__subtitle">
          LA Noire Police Department
        </p>
      </div>

      {error && (
        <Alert type="error" onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <div className="auth-form__fields">
        <Input
          label="Username / Email / Phone / National ID"
          name="identifier"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          error={fieldErrors['identifier']}
          placeholder="Enter your identifier"
          autoComplete="username"
          autoFocus
          required
        />

        <Input
          label="Password"
          name="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldErrors['password']}
          placeholder="Enter your password"
          autoComplete="current-password"
          required
        />
      </div>

      <Button
        type="submit"
        loading={loading}
        fullWidth
        size="lg"
        className="auth-form__submit"
      >
        Sign In
      </Button>

      <p className="auth-form__footer">
        Don&apos;t have an account?{' '}
        <Link to="/register" className="auth-form__link">
          Register
        </Link>
      </p>
    </form>
  );
};
