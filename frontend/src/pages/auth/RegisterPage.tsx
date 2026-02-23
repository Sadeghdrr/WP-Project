/**
 * RegisterPage — wraps RegisterForm inside the AuthLayout card.
 * Route: /register
 */
import { RegisterForm } from '@/features/auth/RegisterForm';

export const RegisterPage: React.FC = () => {
  return <RegisterForm />;
};
