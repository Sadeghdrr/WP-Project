/**
 * RegisterForm — account registration form.
 *
 * Required fields: username, password, password_confirm, email,
 * phone_number, first_name, last_name, national_id.
 *
 * Performs client-side validation (validators.ts) before submitting
 * to POST /accounts/auth/register/.  Server-side field errors are
 * mapped back to individual fields via extractFieldErrors().
 */
import { useState, type FormEvent, type ChangeEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/context/ToastContext';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { extractErrorMessage, extractFieldErrors } from '@/utils/errors';
import {
  validateEmail,
  validatePhoneNumber,
  validateNationalId,
  validatePassword,
} from '@/utils/validators';

interface FormState {
  username: string;
  password: string;
  password_confirm: string;
  email: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  national_id: string;
}

const INITIAL_STATE: FormState = {
  username: '',
  password: '',
  password_confirm: '',
  email: '',
  phone_number: '',
  first_name: '',
  last_name: '',
  national_id: '',
};

export const RegisterForm: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const [form, setForm] = useState<FormState>(INITIAL_STATE);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    // Clear field error on change
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!form.username.trim()) errors['username'] = 'Username is required';
    if (!form.first_name.trim()) errors['first_name'] = 'First name is required';
    if (!form.last_name.trim()) errors['last_name'] = 'Last name is required';

    if (!form.email.trim()) {
      errors['email'] = 'Email is required';
    } else if (!validateEmail(form.email)) {
      errors['email'] = 'Please enter a valid email address';
    }

    if (!form.phone_number.trim()) {
      errors['phone_number'] = 'Phone number is required';
    } else if (!validatePhoneNumber(form.phone_number)) {
      errors['phone_number'] = 'Must be a valid Iranian mobile number (09xxxxxxxxx)';
    }

    if (!form.national_id.trim()) {
      errors['national_id'] = 'National ID is required';
    } else if (!validateNationalId(form.national_id)) {
      errors['national_id'] = 'Must be exactly 10 digits';
    }

    if (!form.password) {
      errors['password'] = 'Password is required';
    } else {
      const pv = validatePassword(form.password);
      if (!pv.valid) {
        errors['password'] = pv.errors[0];
      }
    }

    if (!form.password_confirm) {
      errors['password_confirm'] = 'Please confirm your password';
    } else if (form.password !== form.password_confirm) {
      errors['password_confirm'] = 'Passwords do not match';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validateForm()) return;

    setLoading(true);
    try {
      await register({
        username: form.username.trim(),
        password: form.password,
        password_confirm: form.password_confirm,
        email: form.email.trim(),
        phone_number: form.phone_number.trim(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        national_id: form.national_id.trim(),
      });
      toast.success('Account created successfully! Please sign in.');
      navigate('/login', { replace: true });
    } catch (err) {
      const fe = extractFieldErrors(err);
      if (fe) {
        setFieldErrors((prev) => ({ ...prev, ...fe }));
      }
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit} noValidate>
      <div className="auth-form__header">
        <h1 className="auth-form__title">Create Account</h1>
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
          label="Username"
          name="username"
          value={form.username}
          onChange={handleChange}
          error={fieldErrors['username']}
          placeholder="Choose a username"
          autoComplete="username"
          autoFocus
          required
        />

        <div className="auth-form__row">
          <Input
            label="First Name"
            name="first_name"
            value={form.first_name}
            onChange={handleChange}
            error={fieldErrors['first_name']}
            placeholder="First name"
            autoComplete="given-name"
            required
          />
          <Input
            label="Last Name"
            name="last_name"
            value={form.last_name}
            onChange={handleChange}
            error={fieldErrors['last_name']}
            placeholder="Last name"
            autoComplete="family-name"
            required
          />
        </div>

        <Input
          label="Email"
          name="email"
          type="email"
          value={form.email}
          onChange={handleChange}
          error={fieldErrors['email']}
          placeholder="you@example.com"
          autoComplete="email"
          required
        />

        <Input
          label="Phone Number"
          name="phone_number"
          type="tel"
          value={form.phone_number}
          onChange={handleChange}
          error={fieldErrors['phone_number']}
          placeholder="09xxxxxxxxx"
          autoComplete="tel"
          required
        />

        <Input
          label="National ID"
          name="national_id"
          value={form.national_id}
          onChange={handleChange}
          error={fieldErrors['national_id']}
          placeholder="10-digit national ID"
          maxLength={10}
          required
        />

        <Input
          label="Password"
          name="password"
          type="password"
          value={form.password}
          onChange={handleChange}
          error={fieldErrors['password']}
          placeholder="Min. 8 characters"
          autoComplete="new-password"
          required
        />

        <Input
          label="Confirm Password"
          name="password_confirm"
          type="password"
          value={form.password_confirm}
          onChange={handleChange}
          error={fieldErrors['password_confirm']}
          placeholder="Re-enter your password"
          autoComplete="new-password"
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
        Create Account
      </Button>

      <p className="auth-form__footer">
        Already have an account?{' '}
        <Link to="/login" className="auth-form__link">
          Sign In
        </Link>
      </p>
    </form>
  );
};
