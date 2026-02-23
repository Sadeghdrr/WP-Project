/**
 * MostWantedCard — displays a most-wanted suspect's profile card.
 *
 * Shows: photo, name, national ID, days wanted, most_wanted_score,
 * reward/bounty amount, rank number, and case link.
 */
import { Badge } from '@/components/ui/Badge';
import type { SuspectListItem } from '@/types/suspect.types';

interface MostWantedCardProps {
  suspect: SuspectListItem;
  rank: number;
}

export function MostWantedCard({ suspect, rank }: MostWantedCardProps) {
  const rewardFormatted = new Intl.NumberFormat('fa-IR').format(
    (suspect as unknown as { reward_amount: number }).reward_amount ?? 0,
  );

  return (
    <div className="most-wanted-card">
      <div className="most-wanted-card__rank">#{rank}</div>
      <div className="most-wanted-card__photo">
        {(suspect as unknown as { photo: string | null }).photo ? (
          <img
            src={(suspect as unknown as { photo: string }).photo}
            alt={suspect.full_name}
            className="most-wanted-card__img"
          />
        ) : (
          <div className="most-wanted-card__placeholder">&#128100;</div>
        )}
      </div>
      <div className="most-wanted-card__info">
        <h3 className="most-wanted-card__name">{suspect.full_name}</h3>
        <p className="most-wanted-card__id">National ID: {suspect.national_id}</p>
        <div className="most-wanted-card__tags">
          <Badge variant="danger">
            {(suspect as unknown as { days_wanted: number }).days_wanted ?? 0} days wanted
          </Badge>
          <Badge variant="warning">
            Score: {suspect.most_wanted_score}
          </Badge>
        </div>
        <p className="most-wanted-card__reward">
          Bounty: <strong>{rewardFormatted} Rials</strong>
        </p>
        <p className="most-wanted-card__case">
          Case #{suspect.case}
        </p>
      </div>
    </div>
  );
}
