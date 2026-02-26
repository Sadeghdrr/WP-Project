/**
 * CaseReportView — renders the full aggregated report for a single case.
 *
 * Fetches data from GET /api/cases/{id}/report/ (restricted to Judge,
 * Captain, Police Chief, System Admin). Renders:
 *   - Case information
 *   - Personnel involved
 *   - Complainants
 *   - Witnesses
 *   - Evidence & testimonies
 *   - Suspects (with interrogations & trials)
 *   - Status history timeline
 *   - Calculations
 *   - Print button for browser print
 *
 * Requirement: §5.7 General Reporting (300 pts).
 */

import { useParams, Link } from "react-router-dom";
import { Skeleton, ErrorState, EmptyState } from "../../components/ui";
import { useCaseReport, type ReportFetchError } from "../../hooks/useCaseReport";
import type {
  CaseReport,
  ReportPersonRef,
  ReportSuspect,
  ReportStatusEntry,
} from "../../types";
import css from "./CaseReportView.module.css";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function personLabel(p: ReportPersonRef | null): string {
  if (!p) return "—";
  return p.role ? `${p.full_name} (${p.role})` : p.full_name;
}

function formatRials(amount: number): string {
  if (amount >= 1_000_000_000)
    return `${(amount / 1_000_000_000).toFixed(1)}B Rials`;
  if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(0)}M Rials`;
  return `${amount.toLocaleString()} Rials`;
}

function verdictClass(v: string): string {
  if (v === "guilty") return css.badgeGuilty;
  if (v === "innocent") return css.badgeInnocent;
  return css.badge;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CaseInfoSection({ report }: { report: CaseReport }) {
  const c = report.case;
  return (
    <section className={css.section}>
      <h2 className={css.sectionTitle}>Case Information</h2>
      <div className={css.kvGrid}>
        <KV label="Title" value={c.title} />
        <KV label="Status" value={c.status_display} />
        <KV label="Crime Level" value={c.crime_level_display} />
        <KV label="Creation Type" value={c.creation_type} />
        <KV label="Incident Date" value={formatDate(c.incident_date)} />
        <KV label="Location" value={c.location ?? "—"} />
        <KV label="Created At" value={formatDateTime(c.created_at)} />
        <KV label="Updated At" value={formatDateTime(c.updated_at)} />
        <KV label="Rejection Count" value={String(c.rejection_count)} />
      </div>
      {c.description && (
        <div style={{ marginTop: "0.75rem" }}>
          <span className={css.kvLabel}>Description</span>
          <p className={css.kvValue} style={{ marginTop: "0.15rem" }}>
            {c.description}
          </p>
        </div>
      )}
    </section>
  );
}

function PersonnelSection({ report }: { report: CaseReport }) {
  const p = report.personnel;
  const entries: { label: string; person: ReportPersonRef | null }[] = [
    { label: "Created By", person: p.created_by },
    { label: "Approved By", person: p.approved_by },
    { label: "Assigned Detective", person: p.assigned_detective },
    { label: "Assigned Sergeant", person: p.assigned_sergeant },
    { label: "Assigned Captain", person: p.assigned_captain },
    { label: "Assigned Judge", person: p.assigned_judge },
  ];

  return (
    <section className={css.section}>
      <h2 className={css.sectionTitle}>Personnel Involved</h2>
      <div className={css.personnelGrid}>
        {entries.map((e) => (
          <div key={e.label} className={css.personnelCard}>
            <span className={css.personnelRole}>{e.label}</span>
            <span className={css.personnelName}>
              {e.person?.full_name ?? "—"}
            </span>
            {e.person?.role && (
              <span className={css.personnelBadge}>{e.person.role}</span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function ComplainantsSection({ report }: { report: CaseReport }) {
  if (report.complainants.length === 0) return null;
  return (
    <section className={css.section}>
      <h2 className={css.sectionTitle}>
        Complainants ({report.complainants.length})
      </h2>
      <div className={css.tableWrap}>
        <table className={css.dataTable}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Primary</th>
              <th>Status</th>
              <th>Reviewed By</th>
            </tr>
          </thead>
          <tbody>
            {report.complainants.map((c) => (
              <tr key={c.id}>
                <td>{c.user?.full_name ?? "—"}</td>
                <td>{c.is_primary ? "Yes" : "No"}</td>
                <td>
                  <span className={css.badge}>{c.status}</span>
                </td>
                <td>{personLabel(c.reviewed_by)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function WitnessesSection({ report }: { report: CaseReport }) {
  if (report.witnesses.length === 0) return null;
  return (
    <section className={css.section}>
      <h2 className={css.sectionTitle}>
        Witnesses ({report.witnesses.length})
      </h2>
      <div className={css.tableWrap}>
        <table className={css.dataTable}>
          <thead>
            <tr>
              <th>Full Name</th>
              <th>Phone</th>
              <th>National ID</th>
            </tr>
          </thead>
          <tbody>
            {report.witnesses.map((w) => (
              <tr key={w.id}>
                <td>{w.full_name}</td>
                <td>{w.phone_number ?? "—"}</td>
                <td>{w.national_id ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function EvidenceSection({ report }: { report: CaseReport }) {
  if (report.evidence.length === 0) return null;
  return (
    <section className={css.section}>
      <h2 className={css.sectionTitle}>
        Evidence &amp; Testimonies ({report.evidence.length})
      </h2>
      <div className={css.tableWrap}>
        <table className={css.dataTable}>
          <thead>
            <tr>
              <th>Title</th>
              <th>Type</th>
              <th>Registered By</th>
              <th>Created</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {report.evidence.map((e) => (
              <tr key={e.id}>
                <td>{e.title}</td>
                <td>
                  <span className={css.badge}>{e.evidence_type}</span>
                </td>
                <td>{personLabel(e.registered_by)}</td>
                <td>{formatDate(e.created_at)}</td>
                <td>{e.description ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function SuspectCard({ suspect }: { suspect: ReportSuspect }) {
  return (
    <div className={css.suspectCard}>
      <div className={css.suspectHeader}>
        <div>
          <h3 className={css.suspectName}>{suspect.full_name}</h3>
          <span className={css.suspectMeta}>
            NID: {suspect.national_id ?? "—"}
          </span>
        </div>
        <span
          className={`${css.badge} ${suspect.status === "wanted" ? css.badgeWanted : ""}`}
        >
          {suspect.status_display}
        </span>
      </div>

      <div className={css.kvGrid}>
        <KV label="Identified By" value={personLabel(suspect.identified_by)} />
        <KV label="Wanted Since" value={formatDate(suspect.wanted_since)} />
        <KV
          label="Days Wanted"
          value={suspect.days_wanted != null ? String(suspect.days_wanted) : "—"}
        />
        <KV
          label="Sergeant Approval"
          value={suspect.sergeant_approval_status ?? "—"}
        />
        {suspect.approved_by_sergeant && (
          <KV
            label="Approved By Sergeant"
            value={personLabel(suspect.approved_by_sergeant)}
          />
        )}
        {suspect.sergeant_rejection_message && (
          <KV
            label="Rejection Message"
            value={suspect.sergeant_rejection_message}
          />
        )}
      </div>

      {/* Interrogations */}
      {suspect.interrogations.length > 0 && (
        <div className={css.subSection}>
          <h4 className={css.subSectionTitle}>
            Interrogations ({suspect.interrogations.length})
          </h4>
          <div className={css.tableWrap}>
            <table className={css.dataTable}>
              <thead>
                <tr>
                  <th>Detective</th>
                  <th>Sergeant</th>
                  <th>Detective Score</th>
                  <th>Sergeant Score</th>
                  <th>Notes</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {suspect.interrogations.map((ig) => (
                  <tr key={ig.id}>
                    <td>{personLabel(ig.detective)}</td>
                    <td>{personLabel(ig.sergeant)}</td>
                    <td>{ig.detective_guilt_score ?? "—"}</td>
                    <td>{ig.sergeant_guilt_score ?? "—"}</td>
                    <td>{ig.notes ?? "—"}</td>
                    <td>{formatDate(ig.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Trials */}
      {suspect.trials.length > 0 && (
        <div className={css.subSection}>
          <h4 className={css.subSectionTitle}>
            Trials ({suspect.trials.length})
          </h4>
          <div className={css.tableWrap}>
            <table className={css.dataTable}>
              <thead>
                <tr>
                  <th>Judge</th>
                  <th>Verdict</th>
                  <th>Punishment</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {suspect.trials.map((t) => (
                  <tr key={t.id}>
                    <td>{personLabel(t.judge)}</td>
                    <td>
                      <span className={verdictClass(t.verdict)}>
                        {t.verdict}
                      </span>
                    </td>
                    <td>
                      {t.punishment_title
                        ? `${t.punishment_title}${t.punishment_description ? ` — ${t.punishment_description}` : ""}`
                        : "—"}
                    </td>
                    <td>{formatDate(t.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function SuspectsSection({ report }: { report: CaseReport }) {
  if (report.suspects.length === 0) return null;
  return (
    <section className={css.section}>
      <h2 className={css.sectionTitle}>
        Suspects ({report.suspects.length})
      </h2>
      {report.suspects.map((s) => (
        <SuspectCard key={s.id} suspect={s} />
      ))}
    </section>
  );
}

function StatusHistorySection({ history }: { history: ReportStatusEntry[] }) {
  if (history.length === 0) return null;
  return (
    <section className={css.section}>
      <h2 className={css.sectionTitle}>
        Status History ({history.length})
      </h2>
      <ul className={css.timeline}>
        {history.map((entry) => (
          <li key={entry.id} className={css.timelineItem}>
            <span className={css.timelineStatus}>{entry.to_status}</span>
            {entry.from_status && (
              <span className={css.timelineFrom}>
                {" "}
                ← {entry.from_status}
              </span>
            )}
            <div className={css.timelineMeta}>
              {personLabel(entry.changed_by)} &middot;{" "}
              {formatDateTime(entry.created_at)}
            </div>
            {entry.message && (
              <div className={css.timelineMessage}>{entry.message}</div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function CalculationsSection({ report }: { report: CaseReport }) {
  if (!report.calculations) return null;
  const c = report.calculations;
  return (
    <section className={css.section}>
      <h2 className={css.sectionTitle}>Calculations</h2>
      <div className={css.kvGrid}>
        <KV label="Crime Level Degree" value={String(c.crime_level_degree)} />
        <KV
          label="Days Since Creation"
          value={String(c.days_since_creation)}
        />
        <KV
          label="Tracking Threshold"
          value={String(c.tracking_threshold)}
        />
        <KV label="Reward" value={formatRials(c.reward_rials)} />
      </div>
    </section>
  );
}

/** Reusable key-value pair */
function KV({ label, value }: { label: string; value: string }) {
  return (
    <div className={css.kvItem}>
      <span className={css.kvLabel}>{label}</span>
      <span className={css.kvValue}>{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading Skeleton
// ---------------------------------------------------------------------------

function ReportSkeleton() {
  return (
    <div className={css.container}>
      <div className={css.skeletonBlock}>
        <Skeleton height={32} width="60%" />
        <Skeleton height={16} width="40%" />
        <div style={{ marginTop: "1rem" }} />
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} height={120} />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Forbidden State
// ---------------------------------------------------------------------------

function ForbiddenState() {
  return (
    <div className={css.container}>
      <div className={css.forbidden}>
        <div className={css.forbiddenIcon}>🔒</div>
        <h2>Access Denied</h2>
        <p>
          Case reports are restricted to Judge, Captain, and Police Chief
          roles. You do not have permission to view this report.
        </p>
        <Link to="/reports" className={css.forbiddenLink}>
          Back to Reports
        </Link>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page Component
// ---------------------------------------------------------------------------

/**
 * Full case report view — /reports/:caseId
 *
 * Fetches the aggregated report from the backend and renders all required
 * sections: case info, personnel, complainants, witnesses, evidence,
 * suspects (with interrogations & trials), status history, and calculations.
 */
export default function CaseReportView() {
  const { caseId } = useParams<{ caseId: string }>();
  const id = caseId ? Number(caseId) : undefined;
  const { data: report, isLoading, error } = useCaseReport(id);

  // ── Loading ─────────────────────────────────────────────────────────
  if (isLoading) return <ReportSkeleton />;

  // ── Access Denied (403) ─────────────────────────────────────────────
  if (error && (error as ReportFetchError).status === 403) {
    return <ForbiddenState />;
  }

  // ── Other errors ────────────────────────────────────────────────────
  if (error) {
    return (
      <div className={css.container}>
        <ErrorState message={error.message} />
      </div>
    );
  }

  // ── No data ─────────────────────────────────────────────────────────
  if (!report) {
    return (
      <div className={css.container}>
        <EmptyState heading="No Report" message="No report data available." />
      </div>
    );
  }

  // ── Render full report ──────────────────────────────────────────────
  return (
    <div className={css.container}>
      {/* Top bar */}
      <div className={css.topBar}>
        <Link to="/reports" className={css.backLink}>
          ← Back to Reports
        </Link>
        <button
          className={css.printBtn}
          onClick={() => window.print()}
          type="button"
        >
          🖨️ Print Report
        </button>
      </div>

      {/* Title */}
      <h1 className={css.reportTitle}>
        Case Report: {report.case.title}
      </h1>
      <p className={css.reportSubtitle}>
        Case #{report.case.id} &middot; Generated{" "}
        {new Date().toLocaleDateString("en-US", {
          year: "numeric",
          month: "long",
          day: "numeric",
        })}
      </p>

      <CaseInfoSection report={report} />
      <PersonnelSection report={report} />
      <ComplainantsSection report={report} />
      <WitnessesSection report={report} />
      <EvidenceSection report={report} />
      <SuspectsSection report={report} />
      <StatusHistorySection history={report.status_history} />
      <CalculationsSection report={report} />
    </div>
  );
}
