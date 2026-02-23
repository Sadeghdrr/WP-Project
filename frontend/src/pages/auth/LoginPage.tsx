/**
 * LoginPage — wraps LoginForm inside the AuthLayout card.
 * Route: /login
 */
import { LoginForm } from '@/features/auth/LoginForm';

export const LoginPage: React.FC = () => {
  return <LoginForm />;
};
