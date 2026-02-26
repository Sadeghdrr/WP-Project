/**
 * General Reporting page — case list for report access.
 *
 * Requirement (§5.7): Full case reports for Judge/Captain/Police Chief (300 pts).
 *
 * Displays a filterable list of cases. Clicking a case navigates to
 * /reports/:caseId which renders the full aggregated report.
 *
 * Access: The list itself is visible to all authenticated users, but the
 * individual report endpoint (GET /api/cases/{id}/report/) is restricted
 * by the backend to Judge, Captain, Police Chief, and System Administrator.
 */

import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Skeleton, ErrorState, EmptyState } from "../../components/ui";
import { useCases } from "../../hooks";
import { useDebounce } from "../../hooks";
import type { CaseListItem, CrimeLevel } from "../../types";
import css from "./ReportingPage.module.css";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const CRIME_CSS: Record<CrimeLevel, string> = {
  1: css.crimeMinor,
  2: css.crimeMedium,
  3: css.crimeMajor,
  4: css.crimeCritical,
};

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ReportingPage() {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 300);

  const { data, isLoading, error, refetch } = useCases(
    debouncedSearch ? { search: debouncedSearch } : {},
  );
  const navigate = useNavigate();

  const cases: CaseListItem[] = useMemo(() => data ?? [], [data]);

  // ── Loading ──
  if (isLoading) {
    return (
      <div className={css.container}>
        <div className={css.header}>
          <h1>General Reporting</h1>
          <p className={css.subtitle}>
            Select a case to view its full report
          </p>
        </div>
        <div className={css.skeletonRows}>
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} height={36} />
          ))}
        </div>
      </div>
    );
  }

  // ── Error ──
  if (error) {
    return (
      <div className={css.container}>
        <div className={css.header}>
          <h1>General Reporting</h1>
        </div>
        <ErrorState message={error.message} onRetry={() => refetch()} />
      </div>
    );
  }

  // ── Render ──
  return (
    <div className={css.container}>
      <div className={css.header}>
        <h1>General Reporting</h1>
        <p className={css.subtitle}>
          Complete case reports — creation date, evidence, testimonies,
          suspects, criminals, complainants, and all involved personnel.
        </p>
      </div>

      {/* Search bar */}
      <div className={css.toolbar}>
        <input
          className={css.searchInput}
          type="text"
          placeholder="Search cases by title or description…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {cases.length === 0 ? (
        <EmptyState
          heading="No Cases"
          message={
            debouncedSearch
              ? "No cases match your search."
              : "There are no cases in the system yet."
          }
        />
      ) : (
        <div className={css.tableWrap}>
          <table className={css.caseTable}>
            <thead>
              <tr>
                <th>#</th>
                <th>Title</th>
                <th>Status</th>
                <th>Crime Level</th>
                <th>Type</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/reports/${c.id}`)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") navigate(`/reports/${c.id}`);
                  }}
                >
                  <td>{c.id}</td>
                  <td>{c.title}</td>
                  <td>
                    <span className={css.statusBadge}>
                      {c.status_display}
                    </span>
                  </td>
                  <td>
                    <span
                      className={`${css.crimeBadge} ${CRIME_CSS[c.crime_level] ?? ""}`}
                    >
                      {c.crime_level_display}
                    </span>
                  </td>
                  <td>{c.creation_type}</td>
                  <td>{formatDate(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
