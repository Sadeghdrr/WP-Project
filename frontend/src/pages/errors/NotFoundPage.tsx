/**
 * NotFoundPage — 404 Not Found.
 *
 * Catch-all for unmatched routes.
 */
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/Button';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  return (
    <div className="unauthorized-page">
      <div className="unauthorized-page__card">
        <div className="unauthorized-page__code">404</div>
        <h1 className="unauthorized-page__title">Page Not Found</h1>
        <p className="unauthorized-page__message">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>

        <div className="unauthorized-page__actions">
          <Button variant="secondary" onClick={() => navigate(-1)}>
            Go Back
          </Button>
          <Button
            variant="primary"
            onClick={() =>
              navigate(isAuthenticated ? '/dashboard' : '/', { replace: true })
            }
          >
            {isAuthenticated ? 'Dashboard' : 'Home'}
          </Button>
        </div>
      </div>
    </div>
  );
};
