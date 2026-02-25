/**
 * CaseListPage — Cases & Complaints workspace.
 *
 * Requirement (§5.6): View and manage cases/complaints with status visibility,
 * filters, and navigation to case detail.
 */

import { useState, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useCases } from "../../hooks/useCases";
import { useDebounce } from "../../hooks";
import { Skeleton, EmptyState, ErrorState } from "../../components/ui";
import {
  STATUS_LABELS,
  STATUS_COLORS,
  CRIME_LEVEL_LABELS,
  CRIME_LEVEL_COLORS,
} from "../../lib/caseWorkflow";
import type { CaseFilters } from "../../api/cases";
import type { CaseStatus, CrimeLevel } from "../../types";
import styles from "./CaseListPage.module.css";

// Status options for filter dropdown
const STATUS_OPTIONS: { value: CaseStatus; label: string }[] = [
  { value: "complaint_registered", label: "Complaint Registered" },
  { value: "cadet_review", label: "Under Cadet Review" },
  { value: "returned_to_complainant", label: "Returned to Complainant" },
  { value: "officer_review", label: "Under Officer Review" },
  { value: "returned_to_cadet", label: "Returned to Cadet" },
  { value: "voided", label: "Voided" },
  { value: "pending_approval", label: "Pending Approval" },
  { value: "open", label: "Open" },
  { value: "investigation", label: "Under Investigation" },
  { value: "suspect_identified", label: "Suspect Identified" },
  { value: "sergeant_review", label: "Under Sergeant Review" },
  { value: "arrest_ordered", label: "Arrest Ordered" },
  { value: "interrogation", label: "Under Interrogation" },
  { value: "captain_review", label: "Under Captain Review" },
  { value: "chief_review", label: "Under Chief Review" },
  { value: "judiciary", label: "Referred to Judiciary" },
  { value: "closed", label: "Closed" },
];

const CRIME_LEVEL_OPTIONS: { value: CrimeLevel; label: string }[] = [
  { value: 1, label: "Level 3 (Minor)" },
  { value: 2, label: "Level 2 (Medium)" },
  { value: 3, label: "Level 1 (Major)" },
  { value: 4, label: "Critical" },
];

const CREATION_TYPE_OPTIONS = [
  { value: "complaint", label: "Complaint" },
  { value: "crime_scene", label: "Crime Scene" },
];

// Badge component
function StatusBadge({ status }: { status: CaseStatus }) {
  const color = STATUS_COLORS[status] ?? "gray";
  const label = STATUS_LABELS[status] ?? status;
  const colorClass =
    color === "blue"
      ? styles.badgeBlue
      : color === "yellow"
        ? styles.badgeYellow
        : color === "orange"
          ? styles.badgeOrange
          : color === "green"
            ? styles.badgeGreen
            : color === "red"
              ? styles.badgeRed
              : color === "purple"
                ? styles.badgePurple
                : styles.badgeGray;

  return <span className={`${styles.badge} ${colorClass}`}>{label}</span>;
}

function CrimeLevelBadge({ level }: { level: CrimeLevel }) {
  const color = CRIME_LEVEL_COLORS[level] ?? "gray";
  const label = CRIME_LEVEL_LABELS[level] ?? `Level ${level}`;
  const colorClass =
    color === "green"
      ? styles.badgeGreen
      : color === "yellow"
        ? styles.badgeYellow
        : color === "orange"
          ? styles.badgeOrange
          : color === "red"
            ? styles.badgeRed
            : styles.badgeGray;

  return <span className={`${styles.badge} ${colorClass}`}>{label}</span>;
}

export default function CaseListPage() {
  const navigate = useNavigate();

  // Filter state
  const [searchInput, setSearchInput] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [crimeLevelFilter, setCrimeLevelFilter] = useState("");
  const [creationTypeFilter, setCreationTypeFilter] = useState("");

  const debouncedSearch = useDebounce(searchInput, 400);

  // When searchInput is cleared (e.g. via clear button), bypass debounce delay
  const effectiveSearch = searchInput ? debouncedSearch : "";

  const filters: CaseFilters = {};
  if (effectiveSearch) filters.search = effectiveSearch;
  if (statusFilter) filters.status = statusFilter;
  if (crimeLevelFilter) filters.crime_level = Number(crimeLevelFilter);
  if (creationTypeFilter) filters.creation_type = creationTypeFilter;

  const { data: cases, isLoading, error, refetch } = useCases(filters);

  const clearFilters = useCallback(() => {
    setSearchInput("");
    setStatusFilter("");
    setCrimeLevelFilter("");
    setCreationTypeFilter("");
  }, []);

  const hasFilters = !!(searchInput || statusFilter || crimeLevelFilter || creationTypeFilter);

  return (
    <div className={styles.container}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1>Cases &amp; Complaints</h1>
          <p>View, filter, and manage cases and complaint statuses</p>
        </div>
        <div className={styles.headerActions}>
          <Link to="/cases/new/complaint" className={styles.btnPrimary}>
            + File Complaint
          </Link>
          <Link to="/cases/new/crime-scene" className={styles.btnPrimary}>
            + Crime Scene
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.filterGroup}>
          <label htmlFor="search">Search</label>
          <input
            id="search"
            type="text"
            placeholder="Search cases..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </div>

        <div className={styles.filterGroup}>
          <label htmlFor="status">Status</label>
          <select
            id="status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.filterGroup}>
          <label htmlFor="crimeLevel">Crime Level</label>
          <select
            id="crimeLevel"
            value={crimeLevelFilter}
            onChange={(e) => setCrimeLevelFilter(e.target.value)}
          >
            <option value="">All Levels</option>
            {CRIME_LEVEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.filterGroup}>
          <label htmlFor="creationType">Type</label>
          <select
            id="creationType"
            value={creationTypeFilter}
            onChange={(e) => setCreationTypeFilter(e.target.value)}
          >
            <option value="">All Types</option>
            {CREATION_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {hasFilters && (
          <button className={styles.clearBtn} onClick={clearFilters} type="button">
            Clear
          </button>
        )}
      </div>

      {/* Content */}
      {isLoading && (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Status</th>
                <th>Crime Level</th>
                <th>Type</th>
                <th>Detective</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 6 }).map((_, i) => (
                <tr key={i} className={styles.skeletonRow}>
                  <td><Skeleton width={30} /></td>
                  <td><Skeleton width="60%" /></td>
                  <td><Skeleton width={100} /></td>
                  <td><Skeleton width={100} /></td>
                  <td><Skeleton width={80} /></td>
                  <td><Skeleton width={100} /></td>
                  <td><Skeleton width={80} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {error && (
        <ErrorState
          message={error instanceof Error ? error.message : "Failed to load cases"}
          onRetry={() => refetch()}
        />
      )}

      {!isLoading && !error && cases?.length === 0 && (
        <EmptyState
          title="No cases found"
          description={
            hasFilters
              ? "Try adjusting your filters."
              : "No cases have been created yet."
          }
          icon="📂"
          action={
            hasFilters
              ? { label: "Clear filters", onClick: clearFilters }
              : undefined
          }
        />
      )}

      {!isLoading && !error && cases && cases.length > 0 && (
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Title</th>
                <th>Status</th>
                <th>Crime Level</th>
                <th>Type</th>
                <th>Detective</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/cases/${c.id}`)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") navigate(`/cases/${c.id}`);
                  }}
                >
                  <td>#{c.id}</td>
                  <td className={styles.caseTitle}>{c.title}</td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td>
                    <CrimeLevelBadge level={c.crime_level} />
                  </td>
                  <td style={{ textTransform: "capitalize" }}>
                    {c.creation_type === "crime_scene" ? "Crime Scene" : "Complaint"}
                  </td>
                  <td>{c.assigned_detective_name ?? "—"}</td>
                  <td>{new Date(c.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
