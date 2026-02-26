import { Link } from "react-router-dom";
import { Skeleton, ErrorState, EmptyState } from "../../components/ui";
import ImageRenderer from "../../components/ui/ImageRenderer";
import { useMostWanted } from "../../hooks/useSuspects";
import type { MostWantedEntry } from "../../types";
import css from "./MostWantedPage.module.css";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_CLASS: Record<string, string> = {
  wanted: css.statusWanted,
  arrested: css.statusArrested,
};

function formatReward(rials: number): string {
  if (rials >= 1_000_000_000) return `${(rials / 1_000_000_000).toFixed(1)}B Rials`;
  if (rials >= 1_000_000) return `${(rials / 1_000_000).toFixed(0)}M Rials`;
  return `${rials.toLocaleString()} Rials`;
}

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------

function MostWantedCard({
  entry,
  rank,
}: {
  entry: MostWantedEntry;
  rank: number;
}) {
  return (
    <article className={css.card}>
      <div className={css.cardTop}>
        <span className={css.rankBadge}>{rank}</span>
        <ImageRenderer
          src={entry.photo}
          alt={entry.full_name}
          requiresAuth={false}
          preview={true}
          placeholderIcon="👤"
          style={{ width: "80px", height: "80px", borderRadius: "8px", flexShrink: 0 }}
        />
        <div className={css.info}>
          <h3 className={css.name}>{entry.full_name}</h3>
          <p className={css.nationalId}>ID: {entry.national_id}</p>
          <span
            className={`${css.statusBadge} ${STATUS_CLASS[entry.status] ?? ""}`}
          >
            {entry.status_display}
          </span>
        </div>
      </div>

      {entry.description && (
        <p className={css.description}>{entry.description}</p>
      )}

      <div className={css.stats}>
        <div className={css.stat}>
          <p className={css.statLabel}>Days Wanted</p>
          <p className={css.statValue}>{entry.days_wanted}</p>
        </div>
        <div className={css.stat}>
          <p className={css.statLabel}>Score</p>
          <p className={css.statValue}>{entry.most_wanted_score}</p>
        </div>
        <div className={css.stat}>
          <p className={css.statLabel}>Since</p>
          <p className={css.statValue}>
            {new Date(entry.wanted_since).toLocaleDateString()}
          </p>
        </div>
      </div>

      <div className={css.rewardFooter}>
        <p className={css.rewardLabel}>Bounty Reward</p>
        <p className={css.rewardAmount}>{formatReward(entry.reward_amount)}</p>
      </div>

      {entry.case_title && (
        <Link to={`/cases/${entry.case}`} className={css.caseLink}>
          Case: {entry.case_title}
        </Link>
      )}
    </article>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

/**
 * Most Wanted page (§5.5, 300 pts).
 *
 * Displays criminals wanted for over 30 days, ranked by
 * score = max_days_wanted × max_crime_degree.
 * Bounty = score × 20,000,000 Rials.
 */
export default function MostWantedPage() {
  const { data, isLoading, error, refetch } = useMostWanted();

  if (isLoading) {
    return (
      <div className={css.container}>
        <div className={css.header}>
          <h1>Most Wanted</h1>
        </div>
        <div className={css.grid}>
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} height={280} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={css.container}>
        <ErrorState message={error.message} onRetry={() => refetch()} />
      </div>
    );
  }

  const entries = data ?? [];

  return (
    <div className={css.container}>
      <div className={css.header}>
        <h1>Most Wanted</h1>
        <p className={css.subtitle}>
          Suspects wanted for over 30 days — ranked by score and bounty reward
        </p>
      </div>

      {entries.length === 0 ? (
        <EmptyState
          heading="No Most Wanted"
          message="There are currently no suspects on the most-wanted list."
        />
      ) : (
        <div className={css.grid}>
          {entries.map((entry, idx) => (
            <MostWantedCard key={entry.id} entry={entry} rank={idx + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
