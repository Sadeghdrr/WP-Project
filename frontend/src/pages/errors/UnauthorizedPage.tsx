/**
 * UnauthorizedPage — 403 Forbidden.
 *
 * Shown when a user attempts to access a resource they don't have
 * permission for.  Provides navigation options to go back or to
 * the dashboard.
 */
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';

export const UnauthorizedPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  return (
    <div className="unauthorized-page">
      <div className="unauthorized-page__card">
        <div className="unauthorized-page__code">403</div>
        <h1 className="unauthorized-page__title">Access Denied</h1>

        <Alert type="error">
          You do not have the required permissions to view this page.
          Contact your system administrator if you believe this is an error.
        </Alert>

        <div className="unauthorized-page__actions">
          <Button variant="secondary" onClick={() => navigate(-1)}>
            Go Back
          </Button>
          {isAuthenticated && (
            <Button
              variant="primary"
              onClick={() => navigate('/dashboard', { replace: true })}
            >
              Dashboard
            </Button>
          )}
          {!isAuthenticated && (
            <Button
              variant="primary"
              onClick={() => navigate('/login', { replace: true })}
            >
              Sign In
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
