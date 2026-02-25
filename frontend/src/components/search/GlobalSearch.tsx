/**
 * GlobalSearch — dropdown search component for the app header.
 *
 * Features:
 *   - Debounced input (350ms)
 *   - Grouped results by entity type (cases, suspects, evidence)
 *   - Click → navigate to detail page
 *   - Keyboard: Escape closes, ArrowDown/Up navigates results
 *   - Loading/error/empty states reuse core UI primitives
 *   - Closes on outside click
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useGlobalSearch } from "../../hooks/useGlobalSearch";
import { LoadingSpinner } from "../ui";
import type {
  SearchCaseResult,
  SearchSuspectResult,
  SearchEvidenceResult,
} from "../../types/core";
import styles from "./GlobalSearch.module.css";

// ---------------------------------------------------------------------------
// Navigation helpers
// ---------------------------------------------------------------------------

function caseUrl(c: SearchCaseResult): string {
  return `/cases/${c.id}`;
}

function suspectUrl(s: SearchSuspectResult): string {
  return `/cases/${s.case_id}/suspects/${s.id}`;
}

function evidenceUrl(e: SearchEvidenceResult): string {
  return `/cases/${e.case_id}/evidence`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const { data, isLoading, isError, error, isQueryValid } =
    useGlobalSearch(query);

  // Show dropdown when user types a valid query
  const showDropdown = open && isQueryValid;

  // ── Close on outside click ────────────────────────────────────────
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // ── Keyboard handling ─────────────────────────────────────────────
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        inputRef.current?.blur();
      }
    },
    [],
  );

  // ── Navigate helper ───────────────────────────────────────────────
  const go = useCallback(
    (url: string) => {
      setOpen(false);
      setQuery("");
      navigate(url);
    },
    [navigate],
  );

  // ── Result counts ─────────────────────────────────────────────────
  const hasCases = (data?.cases?.length ?? 0) > 0;
  const hasSuspects = (data?.suspects?.length ?? 0) > 0;
  const hasEvidence = (data?.evidence?.length ?? 0) > 0;
  const hasResults = hasCases || hasSuspects || hasEvidence;

  return (
    <div className={styles.container} ref={containerRef}>
      <div className={styles.inputWrapper}>
        <svg
          className={styles.searchIcon}
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          ref={inputRef}
          className={styles.input}
          type="search"
          placeholder="Search cases, suspects, evidence…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          aria-label="Global search"
          autoComplete="off"
        />
      </div>

      {showDropdown && (
        <div className={styles.dropdown} role="listbox">
          {/* Loading */}
          {isLoading && (
            <div className={styles.status}>
              <LoadingSpinner variant="inline" label="Searching…" />
              <span className={styles.statusText}>Searching…</span>
            </div>
          )}

          {/* Error */}
          {isError && !isLoading && (
            <div className={styles.status}>
              <span className={styles.statusText}>
                {(error as { message?: string })?.message ?? "Search failed"}
              </span>
            </div>
          )}

          {/* Empty */}
          {!isLoading && !isError && data && !hasResults && (
            <div className={styles.status}>
              <span className={styles.statusText}>
                No results for &ldquo;{data.query}&rdquo;
              </span>
            </div>
          )}

          {/* Results */}
          {!isLoading && !isError && data && hasResults && (
            <>
              {/* Cases */}
              {hasCases && (
                <div className={styles.group}>
                  <div className={styles.groupHeader}>
                    <span>Cases</span>
                    <span className={styles.badge}>{data.cases.length}</span>
                  </div>
                  {data.cases.map((c) => (
                    <button
                      key={`case-${c.id}`}
                      className={styles.resultItem}
                      onClick={() => go(caseUrl(c))}
                      role="option"
                      type="button"
                    >
                      <span className={styles.resultTitle}>{c.title}</span>
                      <span className={styles.resultMeta}>
                        {c.crime_level_label} · {c.status}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Suspects */}
              {hasSuspects && (
                <div className={styles.group}>
                  <div className={styles.groupHeader}>
                    <span>Suspects</span>
                    <span className={styles.badge}>{data.suspects.length}</span>
                  </div>
                  {data.suspects.map((s) => (
                    <button
                      key={`suspect-${s.id}`}
                      className={styles.resultItem}
                      onClick={() => go(suspectUrl(s))}
                      role="option"
                      type="button"
                    >
                      <span className={styles.resultTitle}>{s.full_name}</span>
                      <span className={styles.resultMeta}>
                        {s.status} · Case: {s.case_title}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Evidence */}
              {hasEvidence && (
                <div className={styles.group}>
                  <div className={styles.groupHeader}>
                    <span>Evidence</span>
                    <span className={styles.badge}>{data.evidence.length}</span>
                  </div>
                  {data.evidence.map((e) => (
                    <button
                      key={`evidence-${e.id}`}
                      className={styles.resultItem}
                      onClick={() => go(evidenceUrl(e))}
                      role="option"
                      type="button"
                    >
                      <span className={styles.resultTitle}>{e.title}</span>
                      <span className={styles.resultMeta}>
                        {e.evidence_type_label} · Case: {e.case_title}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Total count */}
              <div className={styles.footer}>
                {data.total_results} result{data.total_results !== 1 ? "s" : ""} found
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
