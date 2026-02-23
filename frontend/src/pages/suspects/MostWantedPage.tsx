/**
 * MostWantedPage — publicly accessible ranked list of most-wanted suspects (§5.5).
 *
 * Fetches from GET /api/suspects/suspects/most-wanted/.
 * Suspects wanted > 30 days, ranked by most_wanted_score =
 *   max_days_wanted × max_crime_degree.
 * Bounty amount displayed in Rials.
 */
import { useQuery } from '@tanstack/react-query';
import { suspectsApi } from '@/services/api/suspects.api';
import { MostWantedCard } from '@/features/suspects/MostWantedCard';
import { Loader } from '@/components/ui/Loader';
import { Alert } from '@/components/ui/Alert';
import { extractErrorMessage } from '@/utils/errors';

export const MostWantedPage: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['most-wanted'],
    queryFn: () => suspectsApi.mostWanted(),
    retry: 1,
  });

  if (isLoading) return <Loader fullScreen label="Loading most wanted…" />;
  if (error) return (
    <div className="page-error">
      <Alert type="error">{extractErrorMessage(error)}</Alert>
    </div>
  );

  const suspects = data ?? [];

  return (
    <div className="most-wanted-page">
      <div className="page-header">
        <h1 className="page-header__title">Most Wanted</h1>
        <p className="page-header__subtitle">
          Suspects wanted for over 30 days, ranked by severity score
        </p>
      </div>

      {suspects.length === 0 ? (
        <Alert type="info">No most-wanted suspects at this time.</Alert>
      ) : (
        <div className="most-wanted-page__grid">
          {suspects.map((suspect, index) => (
            <MostWantedCard
              key={suspect.id}
              suspect={suspect}
              rank={index + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};
