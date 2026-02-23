/**
 * HomePage — publicly accessible landing page (§5.1).
 *
 * Displays system intro + at least three statistics:
 *  - Total solved cases
 *  - Total employees
 *  - Active cases
 *
 * Fetches aggregated stats from GET /api/core/dashboard/.
 */
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { coreApi } from '@/services/api/core.api';
import { StatsCards } from '@/features/dashboard/StatsCards';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { extractErrorMessage } from '@/utils/errors';

export const HomePage: React.FC = () => {
  const {
    data: stats,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['dashboard-stats-public'],
    queryFn: () => coreApi.dashboardStats(),
    retry: 1,
  });

  return (
    <div className="home-page">
      <section className="home-page__hero">
        <h1 className="home-page__title">LA Noire Police Department</h1>
        <p className="home-page__subtitle">
          Serving justice through rigorous investigation, transparent processes,
          and community trust. Our integrated case management system tracks
          every complaint, evidence item, and suspect from initial report
          through final verdict.
        </p>
        <div className="home-page__actions">
          <Link to="/login">
            <Button variant="primary" size="lg">Sign In</Button>
          </Link>
          <Link to="/most-wanted">
            <Button variant="outline" size="lg">Most Wanted</Button>
          </Link>
        </div>
      </section>

      <section className="home-page__stats">
        <h2 className="home-page__section-title">Department Statistics</h2>
        {error ? (
          <Alert type="error">{extractErrorMessage(error)}</Alert>
        ) : (
          <StatsCards stats={stats ?? null} loading={isLoading} />
        )}
      </section>

      <section className="home-page__features">
        <h2 className="home-page__section-title">System Capabilities</h2>
        <div className="home-page__feature-grid">
          <div className="home-page__feature-card">
            <h3>Case Management</h3>
            <p>Track complaints, crime scenes, and investigations from start to resolution with full audit trails.</p>
          </div>
          <div className="home-page__feature-card">
            <h3>Evidence Vault</h3>
            <p>Register, categorize, and verify evidence — testimonies, biologicals, vehicles, IDs, and more.</p>
          </div>
          <div className="home-page__feature-card">
            <h3>Detective Board</h3>
            <p>Visual investigation boards with drag-and-drop items, red-line connections, and export capability.</p>
          </div>
          <div className="home-page__feature-card">
            <h3>Role-Based Access</h3>
            <p>Dynamic RBAC ensures every user sees only what they&apos;re authorized for — from Cadets to the Chief.</p>
          </div>
        </div>
      </section>
    </div>
  );
};
