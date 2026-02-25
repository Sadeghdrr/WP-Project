import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useBountyTipActions } from "../../hooks/useSuspects";
import type { BountyVerifyLookupResponse } from "../../types";
import css from "./VerifyRewardPage.module.css";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatReward(rials: number): string {
  if (rials >= 1_000_000_000) return `${(rials / 1_000_000_000).toFixed(1)}B Rials`;
  if (rials >= 1_000_000) return `${(rials / 1_000_000).toFixed(0)}M Rials`;
  return `${rials.toLocaleString()} Rials`;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

/**
 * Verify Reward page (§4.8).
 *
 * Police personnel enter a citizen's national ID and the unique code
 * they received after tip verification. Returns reward details.
 */
export default function VerifyRewardPage() {
  const { lookupReward } = useBountyTipActions();
  const [nationalId, setNationalId] = useState("");
  const [uniqueCode, setUniqueCode] = useState("");
  const [formError, setFormError] = useState("");
  const [result, setResult] = useState<BountyVerifyLookupResponse | null>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setFormError("");
    setResult(null);

    if (!nationalId.trim() || !uniqueCode.trim()) {
      setFormError("Both fields are required.");
      return;
    }

    lookupReward.mutate(
      { national_id: nationalId.trim(), unique_code: uniqueCode.trim() },
      {
        onSuccess: (data) => setResult(data),
        onError: (err) => setFormError(err.message),
      },
    );
  };

  return (
    <div className={css.container}>
      <Link to="/bounty-tips" className={css.backLink}>
        ← Back to Bounty Tips
      </Link>

      <div className={css.header}>
        <h1>Verify Reward</h1>
        <p className={css.subtitle}>
          Look up a bounty reward using the citizen's national ID and unique code
        </p>
      </div>

      <form className={css.form} onSubmit={handleSubmit}>
        <div className={css.field}>
          <label htmlFor="nationalId">National ID</label>
          <input
            id="nationalId"
            type="text"
            placeholder="e.g. 0012345678"
            maxLength={10}
            value={nationalId}
            onChange={(e) => setNationalId(e.target.value)}
            required
          />
        </div>

        <div className={css.field}>
          <label htmlFor="uniqueCode">Unique Code</label>
          <input
            id="uniqueCode"
            type="text"
            placeholder="Reward claim code"
            value={uniqueCode}
            onChange={(e) => setUniqueCode(e.target.value)}
            required
          />
        </div>

        {formError && <p className={css.errorText}>{formError}</p>}

        <button
          type="submit"
          className={css.submitBtn}
          disabled={lookupReward.isPending}
        >
          {lookupReward.isPending ? "Looking up…" : "Look Up"}
        </button>
      </form>

      {result && (
        <div className={css.resultCard}>
          <h2>Reward Details</h2>

          <div className={css.resultRow}>
            <span className={css.resultLabel}>Tip ID</span>
            <span className={css.resultValue}>{result.tip_id}</span>
          </div>

          <div className={css.resultRow}>
            <span className={css.resultLabel}>Informant</span>
            <span className={css.resultValue}>{result.informant_name}</span>
          </div>

          <div className={css.resultRow}>
            <span className={css.resultLabel}>National ID</span>
            <span className={css.resultValue}>{result.informant_national_id}</span>
          </div>

          <div className={css.resultRow}>
            <span className={css.resultLabel}>Suspect</span>
            <span className={css.resultValue}>
              {result.suspect_name ?? "—"}
            </span>
          </div>

          {result.case_id && (
            <div className={css.resultRow}>
              <span className={css.resultLabel}>Case</span>
              <span className={css.resultValue}>
                <Link to={`/cases/${result.case_id}`}>
                  Case #{result.case_id}
                </Link>
              </span>
            </div>
          )}

          <div className={css.resultRow}>
            <span className={css.resultLabel}>Reward Amount</span>
            <span className={`${css.resultValue} ${css.rewardHighlight}`}>
              {formatReward(result.reward_amount)}
            </span>
          </div>

          <div className={css.resultRow}>
            <span className={css.resultLabel}>Claimed</span>
            <span
              className={`${css.claimedBadge} ${
                result.is_claimed ? css.claimedYes : css.claimedNo
              }`}
            >
              {result.is_claimed ? "Claimed" : "Not Claimed"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
