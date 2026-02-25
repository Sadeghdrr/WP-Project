import { useState, useMemo, useCallback } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { Skeleton, ErrorState, EmptyState } from "../../components/ui";
import { useEvidence } from "../../hooks/useEvidence";
import { useDebounce } from "../../hooks";
import {
  EVIDENCE_TYPE_LABELS,
  EVIDENCE_TYPE_COLORS,
  EVIDENCE_TYPE_ICONS,
} from "../../lib/evidenceHelpers";
import type { EvidenceFilters } from "../../api/evidence";
import type { EvidenceType } from "../../types";
import css from "./EvidenceListPage.module.css";

const EVIDENCE_TYPES: EvidenceType[] = [
  "testimony",
  "biological",
  "vehicle",
  "identity",
  "other",
];

const COLOR_MAP: Record<string, string> = {
  blue: css.badgeBlue,
  red: css.badgeRed,
  amber: css.badgeAmber,
  purple: css.badgePurple,
  gray: css.badgeGray,
};

/**
 * Evidence list page — nested under /cases/:caseId/evidence.
 *
 * Lists all evidence for the given case with filters for type and search.
 * Links to evidence detail and provides a "Register Evidence" action.
 */
export default function EvidenceListPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();
  const numericCaseId = caseId ? Number(caseId) : undefined;

  // Filters
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const debouncedSearch = useDebounce(search, 300);
  // When search is cleared, bypass stale debounced value immediately
  const effectiveSearch = search ? debouncedSearch : "";

  const filters: EvidenceFilters = useMemo(() => {
    const f: EvidenceFilters = {};
    if (numericCaseId) f.case = numericCaseId;
    if (effectiveSearch) f.search = effectiveSearch;
    if (typeFilter) f.evidence_type = typeFilter;
    return f;
  }, [numericCaseId, effectiveSearch, typeFilter]);

  const { data: evidence, isLoading, isError, error, refetch } = useEvidence(filters);

  const hasActiveFilters = !!search || !!typeFilter;

  const clearFilters = useCallback(() => {
    setSearch("");
    setTypeFilter("");
  }, []);

  const navigateToDetail = useCallback(
    (evidenceId: number) => {
      // Navigate to an evidence detail within this case context
      navigate(`/cases/${caseId}/evidence/${evidenceId}`);
    },
    [navigate, caseId],
  );

  // ── Render ──────────────────────────────────────────────────

  return (
    <div className={css.container}>
      {/* Back link */}
      <Link to={`/cases/${caseId}`} className={css.backLink}>
        ← Back to Case
      </Link>

      {/* Header */}
      <div className={css.header}>
        <h1>Evidence</h1>
        <Link to={`/cases/${caseId}/evidence/new`} className={css.addBtn}>
          + Register Evidence
        </Link>
      </div>

      {/* Filters */}
      <div className={css.filters}>
        <input
          type="text"
          placeholder="Search evidence…"
          className={css.searchInput}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className={css.filterSelect}
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="">All Types</option>
          {EVIDENCE_TYPES.map((t) => (
            <option key={t} value={t}>
              {EVIDENCE_TYPE_LABELS[t]}
            </option>
          ))}
        </select>
        {hasActiveFilters && (
          <button className={css.clearBtn} onClick={clearFilters}>
            Clear
          </button>
        )}
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div>
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className={css.skeletonRow}>
              <Skeleton style={{ width: "5%", height: "1rem" }} />
              <Skeleton style={{ width: "30%", height: "1rem" }} />
              <Skeleton style={{ width: "15%", height: "1rem" }} />
              <Skeleton style={{ width: "20%", height: "1rem" }} />
              <Skeleton style={{ width: "15%", height: "1rem" }} />
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {isError && !isLoading && (
        <ErrorState
          message={error?.message ?? "Failed to load evidence"}
          onRetry={() => refetch()}
        />
      )}

      {/* Empty */}
      {!isLoading && !isError && evidence && evidence.length === 0 && (
        <EmptyState
          title={hasActiveFilters ? "No matching evidence" : "No evidence registered"}
          message={
            hasActiveFilters
              ? "Try adjusting the filters."
              : "Register the first piece of evidence for this case."
          }
        />
      )}

      {/* Data table */}
      {!isLoading && !isError && evidence && evidence.length > 0 && (
        <div className={css.tableWrap}>
          <table className={css.table}>
            <thead>
              <tr>
                <th>#</th>
                <th>Title</th>
                <th>Type</th>
                <th className={css.colRegistrar}>Registered By</th>
                <th className={css.colDate}>Date</th>
              </tr>
            </thead>
            <tbody>
              {evidence.map((item) => {
                const color = EVIDENCE_TYPE_COLORS[item.evidence_type] ?? "gray";
                return (
                  <tr
                    key={item.id}
                    onClick={() => navigateToDetail(item.id)}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") navigateToDetail(item.id);
                    }}
                  >
                    <td>{item.id}</td>
                    <td>
                      {EVIDENCE_TYPE_ICONS[item.evidence_type] ?? "📦"}{" "}
                      {item.title}
                    </td>
                    <td>
                      <span className={`${css.badge} ${COLOR_MAP[color] ?? css.badgeGray}`}>
                        {item.evidence_type_display}
                      </span>
                    </td>
                    <td className={css.colRegistrar}>
                      {item.registered_by_name ?? `User #${item.registered_by}`}
                    </td>
                    <td className={css.colDate}>
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
