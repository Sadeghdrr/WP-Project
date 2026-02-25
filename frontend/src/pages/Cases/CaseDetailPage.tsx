/**
 * CaseDetailPage — Full case detail with workflow actions.
 *
 * Shows: metadata, description, complainants, witnesses, status log,
 * calculations, and a role-aware workflow action panel.
 */

import { useState, useCallback, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useCaseDetail, useCaseActions } from "../../hooks/useCases";
import { useAuth } from "../../auth/useAuth";
import { Skeleton, ErrorState } from "../../components/ui";
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

  if (!caseData) return null;

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
                      {c.user
                        ? `${(c.user as unknown as { first_name: string; last_name: string }).first_name} ${(c.user as unknown as { first_name: string; last_name: string }).last_name}`.trim() || `User #${(c.user as unknown as { id: number }).id}`
                        : "—"}
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
                ? `by ${(log.changed_by as unknown as { first_name: string; last_name: string }).first_name ?? ""} ${(log.changed_by as unknown as { first_name: string; last_name: string }).last_name ?? ""}`.trim() || `User #${(log.changed_by as unknown as { id: number }).id}`
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
  const actions = useCaseActions(caseData.id);

  const availableActions = getAvailableActions(caseData.status, permissionSet);

  const handleAction = useCallback(
    async (action: WorkflowAction) => {
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
        case "declare_suspects":
          await actions.declareSuspects.mutateAsync();
          break;
        case "sergeant_approve":
          await actions.sergeantReview.mutateAsync({ decision: "approve" });
          break;
        case "sergeant_reject":
          await actions.sergeantReview.mutateAsync({ decision: "reject", message });
          break;
        case "transition_interrogation":
          await actions.transitionCase.mutateAsync({ target_status: "interrogation" });
          break;
        case "transition_captain_review":
          await actions.transitionCase.mutateAsync({ target_status: "captain_review" });
          break;
        case "forward_judiciary":
          await actions.forwardToJudiciary.mutateAsync();
          break;
        case "escalate_chief":
          await actions.transitionCase.mutateAsync({ target_status: "chief_review" });
          break;
        case "close_case":
          await actions.transitionCase.mutateAsync({ target_status: "closed" });
          break;
        default:
          throw new Error(`Unknown action: ${action.key}`);
      }
      setToast({ message: `Action "${action.label}" completed successfully`, type: "success" });
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
    actions.declareSuspects.isPending ||
    actions.sergeantReview.isPending ||
    actions.forwardToJudiciary.isPending ||
    actions.transitionCase.isPending;

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
    </>
  );
}
