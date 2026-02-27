/**
 * SuspectDetailPage — Full suspect detail with workflow action panel.
 *
 * Route: /cases/:caseId/suspects/:suspectId
 *
 * Shows: profile info, status/approval badges, sergeant rejection message,
 * workflow actions (approve, arrest, interrogation, verdict, trial, bail),
 * nested interrogation/trial/bail lists.
 */

import { useState, useCallback, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useSuspectDetail, useSuspectActions, useSuspectInterrogations, useSuspectTrials, useSuspectBails } from "../../hooks/useSuspects";
import { useAuth } from "../../auth/useAuth";
import { Skeleton, ErrorState, EmptyState } from "../../components/ui";
import {
  SUSPECT_STATUS_LABELS,
  SUSPECT_STATUS_COLORS,
  APPROVAL_STATUS_LABELS,
  APPROVAL_STATUS_COLORS,
  getSuspectActions,
  isTerminalSuspectStatus,
} from "../../lib/suspectWorkflow";
import type { SuspectStatus, SergeantApprovalStatus, Suspect, Interrogation, Trial, Bail } from "../../types";
import styles from "./Suspects.module.css";

// ---------------------------------------------------------------------------
// Badge helpers
// ---------------------------------------------------------------------------

function SuspectStatusBadge({ status }: { status: SuspectStatus }) {
  const color = SUSPECT_STATUS_COLORS[status] ?? "gray";
  const label = SUSPECT_STATUS_LABELS[status] ?? status;
  const cls = `badge${color.charAt(0).toUpperCase() + color.slice(1)}` as keyof typeof styles;
  return <span className={`${styles.badge} ${styles[cls] ?? styles.badgeGray}`}>{label}</span>;
}

function ApprovalBadge({ status }: { status: SergeantApprovalStatus }) {
  const color = APPROVAL_STATUS_COLORS[status] ?? "gray";
  const label = APPROVAL_STATUS_LABELS[status] ?? status;
  const cls = `badge${color.charAt(0).toUpperCase() + color.slice(1)}` as keyof typeof styles;
  return <span className={`${styles.badge} ${styles[cls] ?? styles.badgeGray}`}>{label}</span>;
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.metaItem}>
      <span className={styles.metaLabel}>{label}</span>
      <span className={styles.metaValue}>{value}</span>
    </div>
  );
}

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

export default function SuspectDetailPage() {
  const { caseId, suspectId } = useParams();
  const cId = caseId ? Number(caseId) : undefined;
  const sId = suspectId ? Number(suspectId) : undefined;

  const { data: suspect, isLoading, error, refetch } = useSuspectDetail(sId);
  const { data: interrogations } = useSuspectInterrogations(sId);
  const { data: trials } = useSuspectTrials(sId);
  const { data: bails } = useSuspectBails(sId);
  const { permissionSet } = useAuth();

  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  if (isLoading) {
    return (
      <div className={styles.container}>
        <Skeleton width={120} />
        <Skeleton variant="rect" height={32} />
        <div className={styles.grid} style={{ marginTop: "1.5rem" }}>
          <div className={styles.section}><Skeleton count={6} /></div>
          <div className={styles.section}><Skeleton count={4} /></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <Link to={`/cases/${cId}/suspects`} className={styles.backLink}>← Back to Suspects</Link>
        <ErrorState
          message={error instanceof Error ? error.message : "Failed to load suspect"}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  if (!suspect) {
    return (
      <div className={styles.container}>
        <Link to={`/cases/${cId}/suspects`} className={styles.backLink}>← Back to Suspects</Link>
        <EmptyState heading="Suspect Not Found" message="No data available for this suspect." />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <Link to={`/cases/${cId}/suspects`} className={styles.backLink}>← Back to Suspects</Link>

      {/* Header */}
      <div className={styles.detailHeader}>
        <div>
          <h1>{suspect.full_name}</h1>
          <div className={styles.headerMeta}>
            <SuspectStatusBadge status={suspect.status} />
            <ApprovalBadge status={suspect.sergeant_approval_status} />
            {suspect.is_most_wanted && (
              <span className={`${styles.badge} ${styles.badgeRed}`}>Most Wanted</span>
            )}
          </div>
        </div>
      </div>

      {/* Sergeant rejection message */}
      {suspect.sergeant_approval_status === "rejected" && suspect.sergeant_rejection_message && (
        <div className={styles.rejectionMsg}>
          <strong>Sergeant Rejection:</strong> {suspect.sergeant_rejection_message}
        </div>
      )}

      {/* Workflow Action Panel */}
      <WorkflowPanel
        suspect={suspect}
        caseId={cId!}
        permissionSet={permissionSet}
        setToast={setToast}
        onActionComplete={() => refetch()}
      />

      {/* Grid */}
      <div className={styles.grid}>
        {/* Profile */}
        <div className={styles.section}>
          <h2>Suspect Profile</h2>
          <div className={styles.metaGrid}>
            <MetaItem label="Full Name" value={suspect.full_name} />
            <MetaItem label="National ID" value={suspect.national_id || "—"} />
            <MetaItem label="Phone" value={suspect.phone_number || "—"} />
            <MetaItem label="Address" value={suspect.address || "—"} />
            <MetaItem label="Wanted Since" value={new Date(suspect.wanted_since).toLocaleString()} />
            <MetaItem label="Days Wanted" value={String(suspect.days_wanted)} />
            {suspect.arrested_at && (
              <MetaItem label="Arrested At" value={new Date(suspect.arrested_at).toLocaleString()} />
            )}
          </div>
        </div>

        {/* Metadata */}
        <div className={styles.section}>
          <h2>Details</h2>
          <div className={styles.metaGrid}>
            <MetaItem label="Case ID" value={`#${suspect.case}`} />
            <MetaItem label="Identified By" value={suspect.identified_by ? `User #${typeof suspect.identified_by === 'object' ? suspect.identified_by.id : suspect.identified_by}` : "—"} />
            <MetaItem label="Approved By" value={suspect.approved_by_sergeant ? `User #${typeof suspect.approved_by_sergeant === 'object' ? suspect.approved_by_sergeant.id : suspect.approved_by_sergeant}` : "—"} />
            <MetaItem label="Most Wanted Score" value={String(suspect.most_wanted_score)} />
            <MetaItem label="Reward" value={`${suspect.reward_amount.toLocaleString()} Rials`} />
          </div>
        </div>

        {/* Description */}
        {suspect.description && (
          <div className={`${styles.section} ${styles.fullWidth}`}>
            <h2>Description</h2>
            <p className={styles.description}>{suspect.description}</p>
          </div>
        )}

        {/* Interrogations */}
        <div className={`${styles.section} ${styles.fullWidth}`}>
          <h2>Interrogations ({interrogations?.length ?? 0})</h2>
          <InterrogationsTable interrogations={interrogations ?? []} />
        </div>

        {/* Trials */}
        <div className={`${styles.section} ${styles.fullWidth}`}>
          <h2>Trials ({trials?.length ?? 0})</h2>
          <TrialsTable trials={trials ?? []} />
        </div>

        {/* Bails */}
        {(bails?.length ?? 0) > 0 && (
          <div className={`${styles.section} ${styles.fullWidth}`}>
            <h2>Bail ({bails!.length})</h2>
            <BailsTable bails={bails!} />
          </div>
        )}
      </div>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Interrogations Table
// ---------------------------------------------------------------------------

function InterrogationsTable({ interrogations }: { interrogations: Interrogation[] }) {
  if (interrogations.length === 0) {
    return <p className={styles.infoText}>No interrogation records yet.</p>;
  }
  return (
    <table className={styles.subTable}>
      <thead>
        <tr>
          <th>ID</th>
          <th>Detective Score</th>
          <th>Sergeant Score</th>
          <th>Notes</th>
          <th>Date</th>
        </tr>
      </thead>
      <tbody>
        {interrogations.map((intg) => (
          <tr key={intg.id}>
            <td>#{intg.id}</td>
            <td>{intg.detective_guilt_score}/10</td>
            <td>{intg.sergeant_guilt_score}/10</td>
            <td>{intg.notes || "—"}</td>
            <td>{new Date(intg.created_at).toLocaleDateString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ---------------------------------------------------------------------------
// Trials Table
// ---------------------------------------------------------------------------

function TrialsTable({ trials }: { trials: Trial[] }) {
  if (trials.length === 0) {
    return <p className={styles.infoText}>No trial records yet.</p>;
  }
  return (
    <table className={styles.subTable}>
      <thead>
        <tr>
          <th>ID</th>
          <th>Verdict</th>
          <th>Punishment</th>
          <th>Judge</th>
          <th>Date</th>
        </tr>
      </thead>
      <tbody>
        {trials.map((trial) => (
          <tr key={trial.id}>
            <td>#{trial.id}</td>
            <td>
              <span className={`${styles.badge} ${trial.verdict === "guilty" ? styles.badgeRed : styles.badgeGreen}`}>
                {trial.verdict}
              </span>
            </td>
            <td>{trial.punishment_title || "—"}</td>
            <td>{trial.judge ? `User #${typeof trial.judge === 'object' ? trial.judge.id : trial.judge}` : "—"}</td>
            <td>{new Date(trial.created_at).toLocaleDateString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ---------------------------------------------------------------------------
// Bails Table
// ---------------------------------------------------------------------------

function BailsTable({ bails }: { bails: Bail[] }) {
  return (
    <table className={styles.subTable}>
      <thead>
        <tr>
          <th>ID</th>
          <th>Amount</th>
          <th>Paid</th>
          <th>Conditions</th>
          <th>Date</th>
        </tr>
      </thead>
      <tbody>
        {bails.map((bail) => (
          <tr key={bail.id}>
            <td>#{bail.id}</td>
            <td>{bail.amount.toLocaleString()} Rials</td>
            <td>
              <span className={`${styles.badge} ${bail.is_paid ? styles.badgeGreen : styles.badgeYellow}`}>
                {bail.is_paid ? "Paid" : "Unpaid"}
              </span>
            </td>
            <td>{bail.conditions || "—"}</td>
            <td>{new Date(bail.created_at).toLocaleDateString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ---------------------------------------------------------------------------
// Workflow Panel
// ---------------------------------------------------------------------------

interface WorkflowPanelProps {
  suspect: Suspect;
  caseId: number;
  permissionSet: ReadonlySet<string>;
  setToast: (t: { message: string; type: "success" | "error" } | null) => void;
  onActionComplete: () => void;
}

function WorkflowPanel({ suspect, caseId, permissionSet, setToast, onActionComplete }: WorkflowPanelProps) {
  const actions = useSuspectActions(suspect.id, caseId);

  // Modal state
  const [activeModal, setActiveModal] = useState<string | null>(null);

  // Form fields
  const [rejectionMessage, setRejectionMessage] = useState("");
  const [arrestLocation, setArrestLocation] = useState("");
  const [arrestNotes, setArrestNotes] = useState("");
  const [verdictNotes, setVerdictNotes] = useState("");
  const [interrogationDetScore, setInterrogationDetScore] = useState(5);
  const [interrogationSgtScore, setInterrogationSgtScore] = useState(5);
  const [interrogationNotes, setInterrogationNotes] = useState("");
  const [trialVerdict, setTrialVerdict] = useState<"guilty" | "innocent">("guilty");
  const [trialPunishmentTitle, setTrialPunishmentTitle] = useState("");
  const [trialPunishmentDesc, setTrialPunishmentDesc] = useState("");
  const [bailAmount, setBailAmount] = useState("");
  const [bailConditions, setBailConditions] = useState("");
  const [chiefNotes, setChiefNotes] = useState("");

  // Update (resubmit) fields
  const [updateFullName, setUpdateFullName] = useState(suspect.full_name);
  const [updateDescription, setUpdateDescription] = useState(suspect.description);
  const [updateAddress, setUpdateAddress] = useState(suspect.address);

  const availableActions = getSuspectActions(
    suspect.status,
    suspect.sergeant_approval_status,
    permissionSet,
  );

  const isAnyLoading =
    actions.approve.isPending ||
    actions.arrest.isPending ||
    actions.transitionStatus.isPending ||
    actions.captainVerdict.isPending ||
    actions.chiefApproval.isPending ||
    actions.updateSuspect.isPending ||
    actions.createInterrogation.isPending ||
    actions.createTrial.isPending ||
    actions.createBail.isPending;

  const closeModal = useCallback(() => {
    setActiveModal(null);
    setRejectionMessage("");
    setArrestLocation("");
    setArrestNotes("");
    setVerdictNotes("");
    setInterrogationDetScore(5);
    setInterrogationSgtScore(5);
    setInterrogationNotes("");
    setTrialPunishmentTitle("");
    setTrialPunishmentDesc("");
    setBailAmount("");
    setBailConditions("");
    setChiefNotes("");
  }, []);

  const handleAction = useCallback(async (key: string) => {
    try {
      switch (key) {
        case "approve":
          await actions.approve.mutateAsync({ decision: "approve" });
          break;
        case "reject":
          setActiveModal("reject");
          return;
        case "update_resubmit":
          setUpdateFullName(suspect.full_name);
          setUpdateDescription(suspect.description);
          setUpdateAddress(suspect.address);
          setActiveModal("update_resubmit");
          return;
        case "arrest":
          setActiveModal("arrest");
          return;
        case "begin_interrogation":
          await actions.transitionStatus.mutateAsync({ target_status: "under_interrogation" });
          break;
        case "create_interrogation":
          setActiveModal("create_interrogation");
          return;
        case "send_to_captain":
          await actions.transitionStatus.mutateAsync({ target_status: "pending_captain_verdict" });
          break;
        case "captain_guilty":
          setActiveModal("captain_guilty");
          return;
        case "captain_innocent":
          setActiveModal("captain_innocent");
          return;
        case "chief_approve":
          await actions.chiefApproval.mutateAsync({ decision: "approve" });
          break;
        case "chief_reject":
          setActiveModal("chief_reject");
          return;
        case "create_trial":
          setActiveModal("create_trial");
          return;
        case "create_bail":
          setActiveModal("create_bail");
          return;
        default:
          throw new Error(`Unknown action: ${key}`);
      }
      setToast({ message: "Action completed successfully", type: "success" });
      onActionComplete();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Action failed", type: "error" });
    }
  }, [actions, suspect, setToast, onActionComplete]);

  // Modal submit handlers
  const handleReject = async () => {
    try {
      await actions.approve.mutateAsync({ decision: "reject", rejection_message: rejectionMessage });
      setToast({ message: "Suspect rejected", type: "success" });
      closeModal();
      onActionComplete();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Failed", type: "error" });
    }
  };

  const handleUpdateResubmit = async () => {
    try {
      await actions.updateSuspect.mutateAsync({
        full_name: updateFullName.trim(),
        description: updateDescription.trim() || undefined,
        address: updateAddress.trim() || undefined,
      });
      // After updating, the backend resets sergeant_approval_status to pending
      setToast({ message: "Suspect updated & resubmitted for approval", type: "success" });
      closeModal();
      onActionComplete();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Failed", type: "error" });
    }
  };

  const handleArrest = async () => {
    try {
      await actions.arrest.mutateAsync({
        arrest_location: arrestLocation.trim(),
        arrest_notes: arrestNotes.trim() || undefined,
      });
      setToast({ message: "Arrest executed", type: "success" });
      closeModal();
      onActionComplete();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Failed", type: "error" });
    }
  };

  const handleCreateInterrogation = async () => {
    try {
      await actions.createInterrogation.mutateAsync({
        case: caseId,
        detective_guilt_score: interrogationDetScore,
        sergeant_guilt_score: interrogationSgtScore,
        notes: interrogationNotes.trim() || undefined,
      });
      setToast({ message: "Interrogation recorded", type: "success" });
      closeModal();
      onActionComplete();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Failed", type: "error" });
    }
  };

  const handleCaptainVerdict = async (verdict: "guilty" | "innocent") => {
    try {
      await actions.captainVerdict.mutateAsync({ verdict, notes: verdictNotes.trim() });
      setToast({ message: `Captain verdict: ${verdict}`, type: "success" });
      closeModal();
      onActionComplete();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Failed", type: "error" });
    }
  };

  const handleChiefReject = async () => {
    try {
      await actions.chiefApproval.mutateAsync({ decision: "reject", notes: chiefNotes.trim() || undefined });
      setToast({ message: "Chief rejected — returned to captain", type: "success" });
      closeModal();
      onActionComplete();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Failed", type: "error" });
    }
  };

  const handleCreateTrial = async () => {
    try {
      await actions.createTrial.mutateAsync({
        case: caseId,
        verdict: trialVerdict,
        punishment_title: trialPunishmentTitle.trim() || undefined,
        punishment_description: trialPunishmentDesc.trim() || undefined,
      });
      setToast({ message: `Trial verdict recorded: ${trialVerdict}`, type: "success" });
      closeModal();
      onActionComplete();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Failed", type: "error" });
    }
  };

  const handleCreateBail = async () => {
    try {
      await actions.createBail.mutateAsync({
        case: caseId,
        amount: Number(bailAmount),
        conditions: bailConditions.trim() || undefined,
      });
      setToast({ message: "Bail set", type: "success" });
      closeModal();
      onActionComplete();
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Failed", type: "error" });
    }
  };

  if (isTerminalSuspectStatus(suspect.status)) {
    return (
      <div className={styles.actionPanel}>
        <h2>Workflow</h2>
        <p className={styles.infoText}>
          This suspect is <strong>{suspect.status}</strong>. No further actions available.
        </p>
      </div>
    );
  }

  if (availableActions.length === 0) {
    return (
      <div className={styles.actionPanel}>
        <h2>Workflow</h2>
        <p className={styles.infoText}>
          No actions available for your role at this stage.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className={styles.actionPanel}>
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
                onClick={() => handleAction(action.key)}
                disabled={isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing…" : action.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* === MODALS === */}

      {/* Reject suspect modal */}
      {activeModal === "reject" && (
        <div className={styles.modalOverlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>Reject Suspect</h3>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Rejection Reason *</label>
              <textarea
                className={styles.formTextarea}
                value={rejectionMessage}
                onChange={(e) => setRejectionMessage(e.target.value)}
                placeholder="Reason for rejection..."
                autoFocus
              />
            </div>
            <div className={styles.modalActions}>
              <button className={styles.btnDefault} onClick={closeModal} type="button">Cancel</button>
              <button
                className={styles.btnDanger}
                onClick={handleReject}
                disabled={!rejectionMessage.trim() || isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing…" : "Reject"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Update & Resubmit modal */}
      {activeModal === "update_resubmit" && (
        <div className={styles.modalOverlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>Update & Resubmit for Approval</h3>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Full Name *</label>
              <input
                className={styles.formInput}
                value={updateFullName}
                onChange={(e) => setUpdateFullName(e.target.value)}
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Address</label>
              <input
                className={styles.formInput}
                value={updateAddress}
                onChange={(e) => setUpdateAddress(e.target.value)}
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Description</label>
              <textarea
                className={styles.formTextarea}
                value={updateDescription}
                onChange={(e) => setUpdateDescription(e.target.value)}
              />
            </div>
            <div className={styles.modalActions}>
              <button className={styles.btnDefault} onClick={closeModal} type="button">Cancel</button>
              <button
                className={styles.btnPrimary}
                onClick={handleUpdateResubmit}
                disabled={!updateFullName.trim() || isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing…" : "Update & Resubmit"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Arrest modal */}
      {activeModal === "arrest" && (
        <div className={styles.modalOverlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>Execute Arrest</h3>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Arrest Location *</label>
              <input
                className={styles.formInput}
                value={arrestLocation}
                onChange={(e) => setArrestLocation(e.target.value)}
                placeholder="Where was the suspect arrested?"
                autoFocus
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Notes</label>
              <textarea
                className={styles.formTextarea}
                value={arrestNotes}
                onChange={(e) => setArrestNotes(e.target.value)}
                placeholder="Additional arrest notes..."
              />
            </div>
            <div className={styles.modalActions}>
              <button className={styles.btnDefault} onClick={closeModal} type="button">Cancel</button>
              <button
                className={styles.btnPrimary}
                onClick={handleArrest}
                disabled={!arrestLocation.trim() || isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing…" : "Execute Arrest"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Interrogation modal */}
      {activeModal === "create_interrogation" && (
        <div className={styles.modalOverlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>Record Interrogation</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
              <div className={styles.formGroup}>
                <label className={styles.formLabel}>Detective Guilt Score (1-10) *</label>
                <input
                  className={styles.scoreInput}
                  type="number"
                  min={1}
                  max={10}
                  value={interrogationDetScore}
                  onChange={(e) => setInterrogationDetScore(Number(e.target.value))}
                />
              </div>
              <div className={styles.formGroup}>
                <label className={styles.formLabel}>Sergeant Guilt Score (1-10) *</label>
                <input
                  className={styles.scoreInput}
                  type="number"
                  min={1}
                  max={10}
                  value={interrogationSgtScore}
                  onChange={(e) => setInterrogationSgtScore(Number(e.target.value))}
                />
              </div>
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Notes</label>
              <textarea
                className={styles.formTextarea}
                value={interrogationNotes}
                onChange={(e) => setInterrogationNotes(e.target.value)}
                placeholder="Interrogation notes..."
              />
            </div>
            <div className={styles.modalActions}>
              <button className={styles.btnDefault} onClick={closeModal} type="button">Cancel</button>
              <button
                className={styles.btnPrimary}
                onClick={handleCreateInterrogation}
                disabled={interrogationDetScore < 1 || interrogationDetScore > 10 || interrogationSgtScore < 1 || interrogationSgtScore > 10 || isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing…" : "Record"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Captain Guilty verdict modal */}
      {activeModal === "captain_guilty" && (
        <div className={styles.modalOverlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>Captain Verdict: Guilty</h3>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Notes *</label>
              <textarea
                className={styles.formTextarea}
                value={verdictNotes}
                onChange={(e) => setVerdictNotes(e.target.value)}
                placeholder="Verdict reasoning..."
                autoFocus
              />
            </div>
            <div className={styles.modalActions}>
              <button className={styles.btnDefault} onClick={closeModal} type="button">Cancel</button>
              <button
                className={styles.btnDanger}
                onClick={() => handleCaptainVerdict("guilty")}
                disabled={!verdictNotes.trim() || isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing…" : "Verdict: Guilty"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Captain Innocent verdict modal */}
      {activeModal === "captain_innocent" && (
        <div className={styles.modalOverlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>Captain Verdict: Innocent</h3>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Notes *</label>
              <textarea
                className={styles.formTextarea}
                value={verdictNotes}
                onChange={(e) => setVerdictNotes(e.target.value)}
                placeholder="Verdict reasoning..."
                autoFocus
              />
            </div>
            <div className={styles.modalActions}>
              <button className={styles.btnDefault} onClick={closeModal} type="button">Cancel</button>
              <button
                className={styles.btnPrimary}
                onClick={() => handleCaptainVerdict("innocent")}
                disabled={!verdictNotes.trim() || isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing…" : "Verdict: Innocent"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Chief Reject modal */}
      {activeModal === "chief_reject" && (
        <div className={styles.modalOverlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>Chief Rejection</h3>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Notes</label>
              <textarea
                className={styles.formTextarea}
                value={chiefNotes}
                onChange={(e) => setChiefNotes(e.target.value)}
                placeholder="Rejection notes..."
                autoFocus
              />
            </div>
            <div className={styles.modalActions}>
              <button className={styles.btnDefault} onClick={closeModal} type="button">Cancel</button>
              <button
                className={styles.btnDanger}
                onClick={handleChiefReject}
                disabled={isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing…" : "Reject"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Trial modal */}
      {activeModal === "create_trial" && (
        <div className={styles.modalOverlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>Record Trial Verdict</h3>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Verdict *</label>
              <select
                className={styles.formSelect}
                value={trialVerdict}
                onChange={(e) => setTrialVerdict(e.target.value as "guilty" | "innocent")}
              >
                <option value="guilty">Guilty</option>
                <option value="innocent">Innocent</option>
              </select>
            </div>
            {trialVerdict === "guilty" && (
              <>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>Punishment Title</label>
                  <input
                    className={styles.formInput}
                    value={trialPunishmentTitle}
                    onChange={(e) => setTrialPunishmentTitle(e.target.value)}
                    placeholder="e.g. Imprisonment"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label className={styles.formLabel}>Punishment Description</label>
                  <textarea
                    className={styles.formTextarea}
                    value={trialPunishmentDesc}
                    onChange={(e) => setTrialPunishmentDesc(e.target.value)}
                    placeholder="Sentencing details..."
                  />
                </div>
              </>
            )}
            <div className={styles.modalActions}>
              <button className={styles.btnDefault} onClick={closeModal} type="button">Cancel</button>
              <button
                className={trialVerdict === "guilty" ? styles.btnDanger : styles.btnPrimary}
                onClick={handleCreateTrial}
                disabled={isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing…" : `Record: ${trialVerdict}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Bail modal */}
      {activeModal === "create_bail" && (
        <div className={styles.modalOverlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>Set Bail</h3>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Amount (Rials) *</label>
              <input
                className={styles.formInput}
                type="number"
                min={0}
                value={bailAmount}
                onChange={(e) => setBailAmount(e.target.value)}
                placeholder="Bail amount"
                autoFocus
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Conditions</label>
              <textarea
                className={styles.formTextarea}
                value={bailConditions}
                onChange={(e) => setBailConditions(e.target.value)}
                placeholder="Bail conditions..."
              />
            </div>
            <div className={styles.modalActions}>
              <button className={styles.btnDefault} onClick={closeModal} type="button">Cancel</button>
              <button
                className={styles.btnPrimary}
                onClick={handleCreateBail}
                disabled={!bailAmount || Number(bailAmount) <= 0 || isAnyLoading}
                type="button"
              >
                {isAnyLoading ? "Processing…" : "Set Bail"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
