import { useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Skeleton, ErrorState, EmptyState } from "../../components/ui";
import { useAuth } from "../../auth/useAuth";
import { useBountyTips, useBountyTipActions } from "../../hooks/useSuspects";
import type { BountyTipFilters } from "../../api/suspects";
import type { BountyTipListItem } from "../../types";
import css from "./BountyTipsPage.module.css";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_BADGE: Record<string, string> = {
  pending: css.badgePending,
  officer_reviewed: css.badgeReviewed,
  verified: css.badgeVerified,
  rejected: css.badgeRejected,
};

const STATUS_LABEL: Record<string, string> = {
  pending: "Pending",
  officer_reviewed: "Reviewed",
  verified: "Verified",
  rejected: "Rejected",
};

// ---------------------------------------------------------------------------
// Inline action row for review/verify
// ---------------------------------------------------------------------------

function TipActionCell({
  tip,
  hierarchyLevel,
}: {
  tip: BountyTipListItem;
  hierarchyLevel: number;
}) {
  const { reviewTip, verifyTip } = useBountyTipActions();
  const [notes, setNotes] = useState("");

  // Officer (hierarchy >= 3) can review pending tips
  const canReview = tip.status === "pending" && hierarchyLevel >= 3;
  // Detective (hierarchy >= 4) can verify officer_reviewed tips
  const canVerify = tip.status === "officer_reviewed" && hierarchyLevel >= 4;

  const handleReview = useCallback(
    (decision: "accept" | "reject") => {
      reviewTip.mutate({
        id: tip.id,
        data: { decision, review_notes: notes || undefined },
      });
    },
    [reviewTip, tip.id, notes],
  );

  const handleVerify = useCallback(
    (decision: "verify" | "reject") => {
      verifyTip.mutate({
        id: tip.id,
        data: { decision, verification_notes: notes || undefined },
      });
    },
    [verifyTip, tip.id, notes],
  );

  if (!canReview && !canVerify) return <td>—</td>;

  const isPending = reviewTip.isPending || verifyTip.isPending;

  return (
    <td>
      <div className={css.actionGroup}>
        <input
          className={css.notesInput}
          placeholder="Notes…"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        {canReview && (
          <>
            <button
              className={`${css.actionBtn} ${css.acceptBtn}`}
              onClick={() => handleReview("accept")}
              disabled={isPending}
            >
              Accept
            </button>
            <button
              className={`${css.actionBtn} ${css.rejectBtn}`}
              onClick={() => handleReview("reject")}
              disabled={isPending}
            >
              Reject
            </button>
          </>
        )}
        {canVerify && (
          <>
            <button
              className={`${css.actionBtn} ${css.acceptBtn}`}
              onClick={() => handleVerify("verify")}
              disabled={isPending}
            >
              Verify
            </button>
            <button
              className={`${css.actionBtn} ${css.rejectBtn}`}
              onClick={() => handleVerify("reject")}
              disabled={isPending}
            >
              Reject
            </button>
          </>
        )}
      </div>
    </td>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

/**
 * Bounty Tips list page (§4.8).
 *
 * Lists all bounty tips (role-scoped). Officers may review, detectives
 * may verify. Links to submit new tip and verify reward.
 */
export default function BountyTipsPage() {
  const { hierarchyLevel } = useAuth();
  const [statusFilter, setStatusFilter] = useState("");

  const filters: BountyTipFilters = {};
  if (statusFilter) filters.status = statusFilter;

  const { data, isLoading, error, refetch } = useBountyTips(filters);

  if (isLoading) {
    return (
      <div className={css.container}>
        <div className={css.header}><h1>Bounty Tips</h1></div>
        <Skeleton height={300} />
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

  const tips: BountyTipListItem[] = data ?? [];

  return (
    <div className={css.container}>
      <div className={css.header}>
        <h1>Bounty Tips</h1>
        <div className={css.actions}>
          <Link to="/bounty-tips/new" className={css.btnPrimary}>
            + Submit Tip
          </Link>
          {hierarchyLevel >= 3 && (
            <Link to="/bounty-tips/verify" className={css.btnSecondary}>
              Verify Reward
            </Link>
          )}
        </div>
      </div>

      <div className={css.filters}>
        <select
          className={css.filterSelect}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="officer_reviewed">Reviewed</option>
          <option value="verified">Verified</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      {tips.length === 0 ? (
        <EmptyState
          heading="No Tips Found"
          message="There are no bounty tips matching the current filter."
        />
      ) : (
        <div className={css.tableWrap}>
        <table className={css.table}>
          <thead>
            <tr>
              <th>ID</th>
              <th>Informant</th>
              <th>Suspect</th>
              <th>Case</th>
              <th>Status</th>
              <th>Claimed</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {tips.map((tip) => (
              <tr key={tip.id}>
                <td>{tip.id}</td>
                <td>{tip.informant_name ?? `User #${tip.informant}`}</td>
                <td>{tip.suspect ?? "—"}</td>
                <td>
                  {tip.case ? (
                    <Link to={`/cases/${tip.case}`}>#{tip.case}</Link>
                  ) : (
                    "—"
                  )}
                </td>
                <td>
                  <span className={`${css.badge} ${STATUS_BADGE[tip.status] ?? ""}`}>
                    {STATUS_LABEL[tip.status] ?? tip.status_display}
                  </span>
                </td>
                <td>{tip.is_claimed ? "Yes" : "No"}</td>
                <td>{new Date(tip.created_at).toLocaleDateString()}</td>
                <TipActionCell tip={tip} hierarchyLevel={hierarchyLevel} />
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </div>
  );
}
