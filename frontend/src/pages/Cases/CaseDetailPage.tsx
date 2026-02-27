/**
 * CaseDetailPage — Full case detail with workflow actions.
 *
 * Shows: metadata, description, complainants, witnesses, status log,
 * calculations, and a role-aware workflow action panel.
 */

import { useState, useCallback, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useCaseDetail, useCaseActions } from "../../hooks/useCases";
import { useEvidence } from "../../hooks/useEvidence";
import { useCaseSuspects } from "../../hooks/useSuspects";
import { useBoardForCase, useCreateBoard } from "../../hooks";
import { useAuth } from "../../auth/useAuth";
import { Skeleton, ErrorState, EmptyState } from "../../components/ui";
import * as casesApi from "../../api/cases";
import {
  STATUS_LABELS,
  STATUS_COLORS,
  CRIME_LEVEL_LABELS,
  CRIME_LEVEL_COLORS,
  getAvailableActions,
  isTerminalStatus,
} from "../../lib/caseWorkflow";
import type { WorkflowAction } from "../../lib/caseWorkflow";
import type { CaseStatus, CrimeLevel, CaseDetail, CaseStatusLog } from "../../types";
import {
  SUSPECT_STATUS_LABELS,
  SUSPECT_STATUS_COLORS,
  APPROVAL_STATUS_LABELS,
  APPROVAL_STATUS_COLORS,
} from "../../lib/suspectWorkflow";
import type { SuspectStatus, SergeantApprovalStatus } from "../../types";
import styles from "./CaseDetailPage.module.css";

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: CaseStatus }) {
  const color = STATUS_COLORS[status] ?? "gray";
  const label = STATUS_LABELS[status] ?? status;
  const cls = `badge${color.charAt(0).toUpperCase() + color.slice(1)}` as keyof typeof styles;
  return <span className={`${styles.badge} ${styles[cls] ?? styles.badgeGray}`}>{label}</span>;
}

function CrimeLevelBadge({ level }: { level: CrimeLevel }) {
  const color = CRIME_LEVEL_COLORS[level] ?? "gray";
  const label = CRIME_LEVEL_LABELS[level] ?? `Level ${level}`;
  const cls = `badge${color.charAt(0).toUpperCase() + color.slice(1)}` as keyof typeof styles;
  return <span className={`${styles.badge} ${styles[cls] ?? styles.badgeGray}`}>{label}</span>;
}

/** Simple inline toast */
function Toast({ message, type, onClose }: { message: string; type: "success" | "error"; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000);
    return () => clearTimeout(t);
  }, [onClose]);

  return (
    <div className={`${styles.toast} ${type === "success" ? styles.toastSuccess : styles.toastError}`}>
      {message}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CaseDetailPage() {
  const { caseId } = useParams();
  const id = caseId ? Number(caseId) : undefined;
  const { data: caseData, isLoading, error, refetch } = useCaseDetail(id);
  const { permissionSet } = useAuth();

  // Toast state
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  // Modal state for actions requiring a message
  const [modalAction, setModalAction] = useState<WorkflowAction | null>(null);
  const [actionMessage, setActionMessage] = useState("");

  // ── Edit mode state ──────────────────────────────────────────────────────
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editLocation, setEditLocation] = useState("");
  const [editIncidentDate, setEditIncidentDate] = useState("");
  const [editSaving, setEditSaving] = useState(false);

  const startEditing = useCallback(() => {
    if (!caseData) return;
    setEditTitle(caseData.title);
    setEditDescription(caseData.description);
    setEditLocation(caseData.location || "");
    setEditIncidentDate(
      caseData.incident_date
        ? new Date(caseData.incident_date).toISOString().slice(0, 16)
        : "",
    );
    setIsEditing(true);
  }, [caseData]);

  const handleCaseSave = useCallback(async () => {
    if (!caseData) return;
    setEditSaving(true);
    try {
      const res = await casesApi.updateCase(caseData.id, {
        title: editTitle.trim(),
        description: editDescription.trim(),
        ...(editLocation.trim() ? { location: editLocation.trim() } : {}),
        ...(editIncidentDate ? { incident_date: editIncidentDate } : {}),
      });
      if (!res.ok) throw new Error(res.error.message);
      await refetch();
      setIsEditing(false);
      setToast({ message: "Case updated successfully", type: "success" });
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : "Update failed",
        type: "error",
      });
    } finally {
      setEditSaving(false);
    }
  }, [caseData, editTitle, editDescription, editLocation, editIncidentDate, refetch]);

  if (isLoading) {
    return (
      <div className={styles.container}>
        <Skeleton width={120} />
        <Skeleton variant="rect" height={32} />
        <div className={styles.grid} style={{ marginTop: "1.5rem" }}>
          <div className={styles.section}>
            <Skeleton count={6} />
          </div>
          <div className={styles.section}>
            <Skeleton count={4} />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <Link to="/cases" className={styles.backLink}>← Back to Cases</Link>
        <ErrorState
          message={error instanceof Error ? error.message : "Failed to load case"}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className={styles.container}>
        <Link to="/cases" className={styles.backLink}>← Back to Cases</Link>
        <EmptyState heading="Case Not Found" message="No data available for this case." />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <Link to="/cases" className={styles.backLink}>← Back to Cases</Link>

      {/* Header */}
      <div className={styles.detailHeader}>
        <div>
          <h1>Case #{caseData.id} — {caseData.title}</h1>
          <div className={styles.headerMeta}>
            <StatusBadge status={caseData.status} />
            <CrimeLevelBadge level={caseData.crime_level} />
            <span className={styles.badge} style={{ background: "#f0f0f0", color: "#555" }}>
              {caseData.creation_type === "crime_scene" ? "Crime Scene" : "Complaint"}
            </span>
          </div>
        </div>
        {permissionSet.has("cases.change_case") && !isTerminalStatus(caseData.status) && (
          <div style={{ display: "flex", gap: "0.5rem", alignSelf: "flex-start" }}>
            {!isEditing ? (
              <button className={styles.btnDefault} onClick={startEditing} type="button">
                ✏️ Edit Case
              </button>
            ) : (
              <>
                <button
                  className={styles.btnDefault}
                  onClick={() => setIsEditing(false)}
                  type="button"
                >
                  Cancel
                </button>
                <button
                  className={styles.btnPrimary}
                  onClick={handleCaseSave}
                  disabled={editSaving || !editTitle.trim()}
                  type="button"
                >
                  {editSaving ? "Saving…" : "Save Changes"}
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Workflow Action Panel */}
      <WorkflowPanel
        caseData={caseData}
        permissionSet={permissionSet}
        modalAction={modalAction}
        setModalAction={setModalAction}
        actionMessage={actionMessage}
        setActionMessage={setActionMessage}
        setToast={setToast}
      />

      {/* Inline case edit form */}
      {isEditing && (
        <div className={styles.section} style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ marginBottom: "1rem" }}>Edit Case</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div>
              <label style={{ fontSize: "0.85rem", fontWeight: 600, display: "block", marginBottom: "0.25rem" }}>Title *</label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                style={{
                  width: "100%", padding: "0.5rem 0.75rem",
                  border: "1px solid #d1d5db", borderRadius: "6px",
                  fontSize: "0.9375rem", boxSizing: "border-box",
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: "0.85rem", fontWeight: 600, display: "block", marginBottom: "0.25rem" }}>Description</label>
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={4}
                style={{
                  width: "100%", padding: "0.5rem 0.75rem",
                  border: "1px solid #d1d5db", borderRadius: "6px",
                  fontSize: "0.9375rem", boxSizing: "border-box", resize: "vertical",
                  fontFamily: "inherit",
                }}
              />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div>
                <label style={{ fontSize: "0.85rem", fontWeight: 600, display: "block", marginBottom: "0.25rem" }}>Location</label>
                <input
                  type="text"
                  value={editLocation}
                  onChange={(e) => setEditLocation(e.target.value)}
                  style={{
                    width: "100%", padding: "0.5rem 0.75rem",
                    border: "1px solid #d1d5db", borderRadius: "6px",
                    fontSize: "0.9375rem", boxSizing: "border-box",
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: "0.85rem", fontWeight: 600, display: "block", marginBottom: "0.25rem" }}>Incident Date</label>
                <input
                  type="datetime-local"
                  value={editIncidentDate}
                  onChange={(e) => setEditIncidentDate(e.target.value)}
                  style={{
                    width: "100%", padding: "0.5rem 0.75rem",
                    border: "1px solid #d1d5db", borderRadius: "6px",
                    fontSize: "0.9375rem", boxSizing: "border-box",
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Grid */}
      <div className={styles.grid}>
        {/* Case Info */}
        <div className={styles.section}>
          <h2>Case Information</h2>
          <div className={styles.metaGrid}>
            <MetaItem label="Status" value={STATUS_LABELS[caseData.status]} />
            <MetaItem
              label="Crime Level"
              value={CRIME_LEVEL_LABELS[caseData.crime_level] ?? String(caseData.crime_level)}
            />
            <MetaItem
              label="Created"
              value={new Date(caseData.created_at).toLocaleString()}
            />
            <MetaItem
              label="Updated"
              value={new Date(caseData.updated_at).toLocaleString()}
            />
            <MetaItem
              label="Incident Date"
              value={caseData.incident_date ? new Date(caseData.incident_date).toLocaleString() : "—"}
            />
            <MetaItem label="Location" value={caseData.location || "—"} />
            {caseData.creation_type === "complaint" && (
              <MetaItem label="Rejection Count" value={`${caseData.rejection_count} / 3`} />
            )}
          </div>
        </div>

        {/* Personnel */}
        <div className={styles.section}>
          <h2>Assigned Personnel</h2>
          <div className={styles.metaGrid}>
            <MetaItem label="Created By" value={caseData.created_by ? `User #${caseData.created_by}` : "—"} />
            <MetaItem label="Approved By" value={caseData.approved_by ? `User #${caseData.approved_by}` : "—"} />
            <MetaItem label="Detective" value={caseData.assigned_detective ? `User #${caseData.assigned_detective}` : "Not assigned"} />
            <MetaItem label="Sergeant" value={caseData.assigned_sergeant ? `User #${caseData.assigned_sergeant}` : "Not assigned"} />
            <MetaItem label="Captain" value={caseData.assigned_captain ? `User #${caseData.assigned_captain}` : "Not assigned"} />
            <MetaItem label="Judge" value={caseData.assigned_judge ? `User #${caseData.assigned_judge}` : "Not assigned"} />
          </div>
        </div>

        {/* Description */}
        <div className={`${styles.section} ${styles.fullWidth}`}>
          <h2>Description</h2>
          <p className={styles.description}>{caseData.description}</p>
        </div>

        {/* Complainants */}
        {caseData.complainants && caseData.complainants.length > 0 && (
          <div className={styles.section}>
            <h2>Complainants ({caseData.complainants.length})</h2>
            <table className={styles.subTable}>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Primary</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {caseData.complainants.map((c) => (
                  <tr key={c.id}>
                    <td>
                      {c.user_display || `User #${c.user}`}
                    </td>
                    <td>{c.is_primary ? "Yes" : "No"}</td>
                    <td>
                      <span
                        className={`${styles.badge} ${
                          c.status === "approved"
                            ? styles.badgeGreen
                            : c.status === "rejected"
                              ? styles.badgeRed
                              : styles.badgeYellow
                        }`}
                      >
                        {c.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Witnesses */}
        {caseData.witnesses && caseData.witnesses.length > 0 && (
          <div className={styles.section}>
            <h2>Witnesses ({caseData.witnesses.length})</h2>
            <table className={styles.subTable}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Phone</th>
                  <th>National ID</th>
                </tr>
              </thead>
              <tbody>
                {caseData.witnesses.map((w) => (
                  <tr key={w.id}>
                    <td>{w.full_name}</td>
                    <td>{w.phone_number}</td>
                    <td>{w.national_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Evidence Section */}
        <EvidenceSection caseId={caseData.id} />

        {/* Suspects Section */}
        <SuspectsSection caseId={caseData.id} caseStatus={caseData.status} />

        {/* Detective Board Section */}
        <DetectiveBoardSection caseId={caseData.id} />

        {/* Calculations */}
        {caseData.calculations && (
          <div className={styles.section}>
            <h2>Calculations</h2>
            <div className={styles.metaGrid}>
              <MetaItem label="Crime Degree" value={String(caseData.calculations.crime_level_degree)} />
              <MetaItem label="Days Since Creation" value={String(caseData.calculations.days_since_creation)} />
              <MetaItem label="Tracking Threshold" value={String(caseData.calculations.tracking_threshold)} />
              <MetaItem
                label="Reward"
                value={`${caseData.calculations.reward_rials.toLocaleString()} Rials`}
              />
            </div>
          </div>
        )}

        {/* Status Log */}
        <div className={`${styles.section} ${styles.fullWidth}`}>
          <h2>Status History</h2>
          <StatusTimeline logs={caseData.status_logs ?? []} />
        </div>
      </div>

      {/* Toast */}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MetaItem helper
// ---------------------------------------------------------------------------

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.metaItem}>
      <span className={styles.metaLabel}>{label}</span>
      <span className={styles.metaValue}>{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Evidence Section (ثبت شواهد)
// ---------------------------------------------------------------------------

function EvidenceSection({ caseId }: { caseId: number }) {
  const { data: evidenceList, isLoading } = useEvidence({ case: caseId });
  const { permissionSet } = useAuth();

  /** Allow evidence registration for users with relevant permission or detectives+ */
  const canRegister =
    permissionSet.has("evidence.add_evidence") ||
    permissionSet.has("evidence.add_testimony") ||
    permissionSet.has("evidence.add_biologicalevidence") ||
    permissionSet.size > 0; // fallback: any authenticated user can navigate, backend enforces

  const count = evidenceList?.length ?? 0;

  return (
    <div className={styles.section}>
      <h2>Evidence ({isLoading ? "…" : count})</h2>
      {isLoading ? (
        <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>Loading evidence…</p>
      ) : count > 0 ? (
        <table className={styles.subTable}>
          <thead>
            <tr>
              <th>Title</th>
              <th>Type</th>
              <th>Registered</th>
            </tr>
          </thead>
          <tbody>
            {evidenceList!.slice(0, 5).map((ev) => (
              <tr key={ev.id}>
                <td>
                  <Link to={`/cases/${caseId}/evidence/${ev.id}`} style={{ color: "var(--color-primary, #4f46e5)" }}>
                    {ev.title}
                  </Link>
                </td>
                <td>{ev.evidence_type_display || ev.evidence_type}</td>
                <td>{new Date(ev.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>
          No evidence registered for this case yet.
        </p>
      )}
      <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.75rem" }}>
        {canRegister && (
          <Link to={`/cases/${caseId}/evidence/new`} className={styles.btnPrimary}>
            + Register Evidence
          </Link>
        )}
        <Link to={`/cases/${caseId}/evidence`} className={styles.btnDefault}>
          View All Evidence
        </Link>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Suspects Section
// ---------------------------------------------------------------------------

function SuspectStatusBadgeInline({ status }: { status: SuspectStatus }) {
  const color = SUSPECT_STATUS_COLORS[status] ?? "gray";
  const label = SUSPECT_STATUS_LABELS[status] ?? status;
  const cls = `badge${color.charAt(0).toUpperCase() + color.slice(1)}` as keyof typeof styles;
  return <span className={`${styles.badge} ${styles[cls] ?? styles.badgeGray}`}>{label}</span>;
}

function ApprovalBadgeInline({ status }: { status: SergeantApprovalStatus }) {
  const color = APPROVAL_STATUS_COLORS[status] ?? "gray";
  const label = APPROVAL_STATUS_LABELS[status] ?? status;
  const cls = `badge${color.charAt(0).toUpperCase() + color.slice(1)}` as keyof typeof styles;
  return <span className={`${styles.badge} ${styles[cls] ?? styles.badgeGray}`}>{label}</span>;
}

function SuspectsSection({ caseId, caseStatus }: { caseId: number; caseStatus: CaseStatus }) {
  const { data: suspects, isLoading } = useCaseSuspects(caseId);
  const { permissionSet } = useAuth();

  // Show section for investigation, judiciary, or closed cases
  const showSection =
    caseStatus === "investigation" || caseStatus === "judiciary" || caseStatus === "closed";
  if (!showSection) return null;

  const canIdentify = permissionSet.has("suspects.can_identify_suspect");
  const count = suspects?.length ?? 0;

  return (
    <div className={styles.section}>
      <h2>Suspects ({isLoading ? "…" : count})</h2>
      {isLoading ? (
        <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>Loading suspects…</p>
      ) : count > 0 ? (
        <table className={styles.subTable}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Approval</th>
            </tr>
          </thead>
          <tbody>
            {suspects!.slice(0, 8).map((s) => (
              <tr key={s.id}>
                <td>
                  <Link to={`/cases/${caseId}/suspects/${s.id}`} style={{ color: "var(--color-primary, #4f46e5)" }}>
                    {s.full_name}
                  </Link>
                </td>
                <td><SuspectStatusBadgeInline status={s.status} /></td>
                <td><ApprovalBadgeInline status={s.sergeant_approval_status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>
          No suspects identified for this case yet.
        </p>
      )}
      <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.75rem" }}>
        {canIdentify && caseStatus === "investigation" && (
          <Link to={`/cases/${caseId}/suspects`} className={styles.btnPrimary}>
            + Identify Suspect
          </Link>
        )}
        <Link to={`/cases/${caseId}/suspects`} className={styles.btnDefault}>
          View All Suspects
        </Link>
        {(caseStatus === "investigation" || caseStatus === "judiciary") && (
          <>
            <Link to={`/cases/${caseId}/interrogations`} className={styles.btnDefault}>
              Interrogations
            </Link>
            <Link to={`/cases/${caseId}/trial`} className={styles.btnDefault}>
              Trial
            </Link>
          </>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detective Board Section
// ---------------------------------------------------------------------------

function DetectiveBoardSection({ caseId }: { caseId: number }) {
  const navigate = useNavigate();
  const { permissionSet } = useAuth();
  const { board, isLoading, error } = useBoardForCase(caseId);
  const createBoardMut = useCreateBoard();

  const canView = permissionSet.has("board.view_detectiveboard");
  const canCreate = permissionSet.has("board.add_detectiveboard");

  // Hide section entirely for users with no board permissions
  if (!canView && !canCreate) return null;

  const handleCreate = () => {
    createBoardMut.mutate(caseId, {
      onSuccess: (newBoard) => {
        navigate(`/detective-board/${caseId}`);
        void newBoard; // board id used implicitly by navigation
      },
    });
  };

  return (
    <div className={styles.section}>
      <h2>Detective Board</h2>
      {isLoading ? (
        <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>Loading board info…</p>
      ) : error ? (
        <p style={{ color: "#991b1b", fontSize: "0.875rem" }}>
          Failed to load board info: {error instanceof Error ? error.message : "Unknown error"}
        </p>
      ) : board ? (
        <>
          <div className={styles.metaGrid}>
            <MetaItem label="Board ID" value={`#${board.id}`} />
            <MetaItem label="Items" value={String(board.item_count)} />
            <MetaItem label="Connections" value={String(board.connection_count)} />
            <MetaItem label="Created" value={new Date(board.created_at).toLocaleDateString()} />
          </div>
          <div style={{ marginTop: "0.75rem" }}>
            <Link to={`/detective-board/${caseId}`} className={styles.btnPrimary}>
              Open Detective Board
            </Link>
          </div>
        </>
      ) : (
        <>
          <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>
            No detective board exists for this case yet.
          </p>
          {canCreate && (
            <div style={{ marginTop: "0.75rem" }}>
              <button
                type="button"
                className={styles.btnPrimary}
                onClick={handleCreate}
                disabled={createBoardMut.isPending}
              >
                {createBoardMut.isPending ? "Creating…" : "Create Detective Board"}
              </button>
              {createBoardMut.isError && (
                <p style={{ color: "#991b1b", fontSize: "0.875rem", marginTop: "0.5rem" }}>
                  {createBoardMut.error.message}
                </p>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Status Timeline
// ---------------------------------------------------------------------------

function StatusTimeline({ logs }: { logs: CaseStatusLog[] }) {
  if (logs.length === 0) {
    return <p style={{ color: "#6b7280", fontSize: "0.875rem" }}>No status changes recorded.</p>;
  }

  return (
    <div className={styles.timeline}>
      {logs.map((log) => (
        <div key={log.id} className={styles.timelineItem}>
          <div className={styles.timelineDot} />
          <div className={styles.timelineContent}>
            <div className={styles.timelineTransition}>
              {STATUS_LABELS[log.from_status] ?? log.from_status} → {STATUS_LABELS[log.to_status] ?? log.to_status}
            </div>
            <div className={styles.timelineMeta}>
              {log.changed_by
                ? `by ${log.changed_by_name || `User #${log.changed_by}`}`
                : "System"}
              {" · "}
              {new Date(log.created_at).toLocaleString()}
            </div>
            {log.message && (
              <div className={styles.timelineMessage}>{log.message}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Workflow Action Panel
// ---------------------------------------------------------------------------

interface WorkflowPanelProps {
  caseData: CaseDetail;
  permissionSet: ReadonlySet<string>;
  modalAction: WorkflowAction | null;
  setModalAction: (a: WorkflowAction | null) => void;
  actionMessage: string;
  setActionMessage: (m: string) => void;
  setToast: (t: { message: string; type: "success" | "error" } | null) => void;
}

function WorkflowPanel({
  caseData,
  permissionSet,
  modalAction,
  setModalAction,
  actionMessage,
  setActionMessage,
  setToast,
}: WorkflowPanelProps) {
  const navigate = useNavigate();
  const actions = useCaseActions(caseData.id);

  // State for assign_detective user selection
  const [assignUserId, setAssignUserId] = useState("");
  const [showAssignModal, setShowAssignModal] = useState(false);

  // State for edit & resubmit
  const [showEditForm, setShowEditForm] = useState(false);
  const [editTitle, setEditTitle] = useState(caseData.title);
  const [editDescription, setEditDescription] = useState(caseData.description);
  const [editLocation, setEditLocation] = useState(caseData.location || "");
  const [editIncidentDate, setEditIncidentDate] = useState(
    caseData.incident_date ? new Date(caseData.incident_date).toISOString().slice(0, 16) : ""
  );
  const [editSubmitting, setEditSubmitting] = useState(false);

  const availableActions = getAvailableActions(caseData.status, permissionSet);

  /** Redirect actions => navigate to /cases after success (prevents 404) */
  const REDIRECT_ACTIONS = new Set([
    "cadet_approve", "officer_approve", "approve_crime_scene",
    "cadet_reforward", "forward_judiciary", "close_case",
  ]);

  const handleAction = useCallback(
    async (action: WorkflowAction) => {
      if (action.key === "assign_detective") {
        setAssignUserId("");
        setShowAssignModal(true);
        return;
      }
      if (action.key === "resubmit") {
        setShowEditForm(true);
        return;
      }
      if (action.needsMessage) {
        setModalAction(action);
        setActionMessage("");
        return;
      }
      await executeAction(action, "");
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [caseData.id, caseData.status],
  );

  const handleAssignDetective = async () => {
    const uid = Number(assignUserId);
    if (!uid || isNaN(uid)) return;
    try {
      await actions.assignDetective.mutateAsync({ user_id: uid });
      setToast({ message: "Detective assigned successfully", type: "success" });
      setShowAssignModal(false);
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : "Failed to assign detective",
        type: "error",
      });
    }
  };

  const handleEditAndResubmit = async () => {
    setEditSubmitting(true);
    try {
      // Step 1: PUT /api/cases/{id} — update case data
      const updateRes = await casesApi.updateCase(caseData.id, {
        title: editTitle.trim(),
        description: editDescription.trim(),
        ...(editLocation.trim() ? { location: editLocation.trim() } : {}),
        ...(editIncidentDate ? { incident_date: editIncidentDate } : {}),
      });
      if (!updateRes.ok) throw new Error(updateRes.error.message);

      // Step 2: POST /api/cases/{id}/resubmit
      await actions.resubmitComplaint.mutateAsync({});
      setToast({ message: "Case updated and resubmitted successfully", type: "success" });
      setShowEditForm(false);
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : "Resubmit failed",
        type: "error",
      });
    } finally {
      setEditSubmitting(false);
    }
  };

  const executeAction = async (action: WorkflowAction, message: string) => {
    try {
      switch (action.key) {
        case "submit":
          await actions.submitForReview.mutateAsync();
          break;
        case "resubmit":
          await actions.resubmitComplaint.mutateAsync({});
          break;
        case "cadet_approve":
          await actions.cadetReview.mutateAsync({ decision: "approve" });
          break;
        case "cadet_reject":
          await actions.cadetReview.mutateAsync({ decision: "reject", message });
          break;
        case "cadet_reforward":
          await actions.transitionCase.mutateAsync({ target_status: "officer_review" });
          break;
        case "officer_approve":
          await actions.officerReview.mutateAsync({ decision: "approve" });
          break;
        case "officer_reject":
          await actions.officerReview.mutateAsync({ decision: "reject", message });
          break;
        case "approve_crime_scene":
          await actions.approveCrimeScene.mutateAsync();
          break;
        case "assign_detective":
          // Handled by handleAssignDetective
          break;
        case "close_case":
          await actions.transitionCase.mutateAsync({ target_status: "closed" });
          break;
        default:
          throw new Error(`Unknown action: ${action.key}`);
      }
      setToast({ message: `Action "${action.label}" completed successfully`, type: "success" });
      // Redirect when the user may lose access to the case after this action
      if (REDIRECT_ACTIONS.has(action.key)) {
        navigate("/cases");
      }
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : "Action failed",
        type: "error",
      });
    }
    setModalAction(null);
  };

  const isAnyLoading =
    actions.submitForReview.isPending ||
    actions.resubmitComplaint.isPending ||
    actions.cadetReview.isPending ||
    actions.officerReview.isPending ||
    actions.approveCrimeScene.isPending ||
    actions.transitionCase.isPending ||
    actions.assignDetective.isPending;

  if (isTerminalStatus(caseData.status)) {
    return (
      <div className={styles.actionPanel} style={{ marginBottom: "1.5rem" }}>
        <h2>Workflow</h2>
        <p style={{ color: "#6b7280", fontSize: "0.875rem", margin: 0 }}>
          This case is <strong>{caseData.status === "closed" ? "closed" : "voided"}</strong>. No further actions available.
        </p>
      </div>
    );
  }

  if (availableActions.length === 0) {
    return (
      <div className={styles.actionPanel} style={{ marginBottom: "1.5rem" }}>
        <h2>Workflow</h2>
        <p style={{ color: "#6b7280", fontSize: "0.875rem", margin: 0 }}>
          No actions available for your role at this stage.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className={styles.actionPanel} style={{ marginBottom: "1.5rem" }}>
        <h2>Workflow Actions</h2>
        <div className={styles.actionButtons}>
          {availableActions.map((action) => {
            const btnClass =
              action.variant === "danger"
                ? styles.btnDanger
                : action.variant === "primary"
                  ? styles.btnPrimary
                  : styles.btnDefault;
            return (
              <button
                key={action.key}
                className={btnClass}
                onClick={() => handleAction(action)}
                disabled={isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing..." : action.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Message modal for rejection actions */}
      {modalAction && (
        <div className={styles.modalOverlay} onClick={() => setModalAction(null)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>{modalAction.label}</h3>
            <textarea
              placeholder="Enter reason / message (required)..."
              value={actionMessage}
              onChange={(e) => setActionMessage(e.target.value)}
              autoFocus
            />
            <div className={styles.modalActions}>
              <button
                className={styles.btnDefault}
                onClick={() => setModalAction(null)}
                type="button"
              >
                Cancel
              </button>
              <button
                className={modalAction.variant === "danger" ? styles.btnDanger : styles.btnPrimary}
                onClick={() => executeAction(modalAction, actionMessage)}
                disabled={!actionMessage.trim() || isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Assign detective modal */}
      {showAssignModal && (
        <div className={styles.modalOverlay} onClick={() => setShowAssignModal(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>Assign Detective</h3>
            <label style={{ fontSize: "0.875rem", color: "#6b7280", marginBottom: "0.5rem", display: "block" }}>
              Enter the User ID of the detective to assign:
            </label>
            <input
              type="number"
              placeholder="User ID"
              value={assignUserId}
              onChange={(e) => setAssignUserId(e.target.value)}
              autoFocus
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                border: "1px solid #d1d5db",
                borderRadius: "0.375rem",
                fontSize: "0.9375rem",
                boxSizing: "border-box",
              }}
            />
            <div className={styles.modalActions}>
              <button
                className={styles.btnDefault}
                onClick={() => setShowAssignModal(false)}
                type="button"
              >
                Cancel
              </button>
              <button
                className={styles.btnPrimary}
                onClick={handleAssignDetective}
                disabled={!assignUserId || isAnyLoading}
                type="button"
              >
                {actions.assignDetective.isPending ? "Assigning…" : "Assign"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit & Resubmit form */}
      {showEditForm && (
        <div className={styles.modalOverlay} onClick={() => setShowEditForm(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()} style={{ maxWidth: 560 }}>
            <h3>Edit &amp; Resubmit Complaint</h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <div>
                <label style={{ fontSize: "0.875rem", fontWeight: 500 }}>Title *</label>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  style={{
                    width: "100%", padding: "0.5rem 0.75rem",
                    border: "1px solid #d1d5db", borderRadius: "0.375rem",
                    fontSize: "0.9375rem", boxSizing: "border-box",
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: "0.875rem", fontWeight: 500 }}>Description *</label>
                <textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  rows={4}
                  style={{
                    width: "100%", padding: "0.5rem 0.75rem",
                    border: "1px solid #d1d5db", borderRadius: "0.375rem",
                    fontSize: "0.9375rem", boxSizing: "border-box", resize: "vertical",
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: "0.875rem", fontWeight: 500 }}>Location</label>
                <input
                  type="text"
                  value={editLocation}
                  onChange={(e) => setEditLocation(e.target.value)}
                  style={{
                    width: "100%", padding: "0.5rem 0.75rem",
                    border: "1px solid #d1d5db", borderRadius: "0.375rem",
                    fontSize: "0.9375rem", boxSizing: "border-box",
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: "0.875rem", fontWeight: 500 }}>Incident Date</label>
                <input
                  type="datetime-local"
                  value={editIncidentDate}
                  onChange={(e) => setEditIncidentDate(e.target.value)}
                  style={{
                    width: "100%", padding: "0.5rem 0.75rem",
                    border: "1px solid #d1d5db", borderRadius: "0.375rem",
                    fontSize: "0.9375rem", boxSizing: "border-box",
                  }}
                />
              </div>
            </div>
            <div className={styles.modalActions}>
              <button
                className={styles.btnDefault}
                onClick={() => setShowEditForm(false)}
                type="button"
              >
                Cancel
              </button>
              <button
                className={styles.btnPrimary}
                onClick={handleEditAndResubmit}
                disabled={editSubmitting || !editTitle.trim() || !editDescription.trim()}
                type="button"
              >
                {editSubmitting ? "Resubmitting…" : "Save & Resubmit"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
