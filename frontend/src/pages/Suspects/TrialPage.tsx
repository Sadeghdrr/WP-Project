/**
 * TrialPage — View & create trial records for suspects under trial.
 *
 * Route: /cases/:caseId/trial
 *
 * Judge reviews case and renders guilty/innocent verdict with sentencing.
 * Also supports setting bail for suspects.
 */

import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useCaseSuspects, useSuspectActions } from "../../hooks/useSuspects";
import { useCaseDetail } from "../../hooks/useCases";
import { useAuth } from "../../auth/useAuth";
import { Skeleton, ErrorState, EmptyState } from "../../components/ui";
import {
  SUSPECT_STATUS_LABELS,
  SUSPECT_STATUS_COLORS,
} from "../../lib/suspectWorkflow";
import type { SuspectStatus, Suspect } from "../../types";
import styles from "./Suspects.module.css";

// ---------------------------------------------------------------------------
// Badge
// ---------------------------------------------------------------------------

function SuspectStatusBadge({ status }: { status: SuspectStatus }) {
  const color = SUSPECT_STATUS_COLORS[status] ?? "gray";
  const label = SUSPECT_STATUS_LABELS[status] ?? status;
  const cls = `badge${color.charAt(0).toUpperCase() + color.slice(1)}` as keyof typeof styles;
  return <span className={`${styles.badge} ${styles[cls] ?? styles.badgeGray}`}>{label}</span>;
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
// Main
// ---------------------------------------------------------------------------

export default function TrialPage() {
  const { caseId } = useParams();
  const cId = caseId ? Number(caseId) : undefined;
  const { data: suspects, isLoading, error, refetch } = useCaseSuspects(cId);
  const { data: caseData } = useCaseDetail(cId);
  const { permissionSet } = useAuth();

  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [trialSuspect, setTrialSuspect] = useState<Suspect | null>(null);
  const [bailSuspect, setBailSuspect] = useState<Suspect | null>(null);

  const canJudge = permissionSet.has("suspects.can_judge_trial");
  const canBail = permissionSet.has("suspects.can_set_bail_amount");

  const underTrial = suspects?.filter((s) => s.status === "under_trial") ?? [];
  const resolved = suspects?.filter((s) =>
    s.status === "convicted" || s.status === "acquitted" || s.status === "released",
  ) ?? [];

  if (isLoading) {
    return (
      <div className={styles.container}>
        <Skeleton width={120} />
        <Skeleton variant="rect" height={32} />
        <Skeleton count={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <Link to={`/cases/${cId}`} className={styles.backLink}>← Back to Case</Link>
        <ErrorState
          message={error instanceof Error ? error.message : "Failed to load suspects"}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <Link to={`/cases/${cId}`} className={styles.backLink}>← Back to Case</Link>

      <div className={styles.detailHeader}>
        <div>
          <h1>Trial — Case #{cId}{caseData ? `: ${caseData.title}` : ""}</h1>
          <div className={styles.headerMeta}>
            <span className={`${styles.badge} ${styles.badgePurple}`}>
              {underTrial.length} under trial
            </span>
            {resolved.length > 0 && (
              <span className={`${styles.badge} ${styles.badgeGreen}`}>
                {resolved.length} resolved
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Suspects Under Trial */}
      {underTrial.length === 0 ? (
        <EmptyState
          heading="No Suspects Under Trial"
          message="No suspects have reached trial status for this case. Suspects must complete interrogation and receive captain/chief approval first."
        />
      ) : (
        <div className={`${styles.section} ${styles.fullWidth}`}>
          <h2>Suspects Under Trial</h2>
          <table className={styles.subTable}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {underTrial.map((s) => (
                <tr key={s.id}>
                  <td>
                    <Link
                      to={`/cases/${cId}/suspects/${s.id}`}
                      style={{ color: "var(--color-primary, #4f46e5)", fontWeight: 600, textDecoration: "none" }}
                    >
                      {s.full_name}
                    </Link>
                  </td>
                  <td><SuspectStatusBadge status={s.status} /></td>
                  <td>
                    <div className={styles.actionButtons}>
                      {canJudge && (
                        <button
                          className={`${styles.btnPrimary} ${styles.btnSmall}`}
                          onClick={() => setTrialSuspect(s)}
                          type="button"
                        >
                          Record Verdict
                        </button>
                      )}
                      {canBail && (
                        <button
                          className={`${styles.btnDefault} ${styles.btnSmall}`}
                          onClick={() => setBailSuspect(s)}
                          type="button"
                        >
                          Set Bail
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Resolved suspects */}
      {resolved.length > 0 && (
        <div className={`${styles.section} ${styles.fullWidth}`} style={{ marginTop: "1.5rem" }}>
          <h2>Resolved ({resolved.length})</h2>
          <table className={styles.subTable}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Outcome</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {resolved.map((s) => (
                <tr key={s.id}>
                  <td>{s.full_name}</td>
                  <td><SuspectStatusBadge status={s.status} /></td>
                  <td>
                    <Link
                      to={`/cases/${cId}/suspects/${s.id}`}
                      className={`${styles.btnDefault} ${styles.btnSmall}`}
                      style={{ textDecoration: "none" }}
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Trial verdict modal */}
      {trialSuspect && cId && (
        <TrialFormModal
          suspect={trialSuspect}
          caseId={cId}
          onClose={() => setTrialSuspect(null)}
          onSuccess={() => {
            setTrialSuspect(null);
            setToast({ message: "Trial verdict recorded", type: "success" });
            refetch();
          }}
          onError={(msg) => setToast({ message: msg, type: "error" })}
        />
      )}

      {/* Bail modal */}
      {bailSuspect && cId && (
        <BailFormModal
          suspect={bailSuspect}
          caseId={cId}
          onClose={() => setBailSuspect(null)}
          onSuccess={() => {
            setBailSuspect(null);
            setToast({ message: "Bail set successfully", type: "success" });
            refetch();
          }}
          onError={(msg) => setToast({ message: msg, type: "error" })}
        />
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Trial Form Modal
// ---------------------------------------------------------------------------

function TrialFormModal({
  suspect,
  caseId,
  onClose,
  onSuccess,
  onError,
}: {
  suspect: Suspect;
  caseId: number;
  onClose: () => void;
  onSuccess: () => void;
  onError: (msg: string) => void;
}) {
  const actions = useSuspectActions(suspect.id, caseId);
  const [verdict, setVerdict] = useState<"guilty" | "innocent">("guilty");
  const [punishmentTitle, setPunishmentTitle] = useState("");
  const [punishmentDesc, setPunishmentDesc] = useState("");

  const handleSubmit = async () => {
    try {
      await actions.createTrial.mutateAsync({
        case: caseId,
        verdict,
        punishment_title: punishmentTitle.trim() || undefined,
        punishment_description: punishmentDesc.trim() || undefined,
      });
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to record trial");
    }
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h3>Trial Verdict — {suspect.full_name}</h3>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>Verdict *</label>
          <select
            className={styles.formSelect}
            value={verdict}
            onChange={(e) => setVerdict(e.target.value as "guilty" | "innocent")}
          >
            <option value="guilty">Guilty</option>
            <option value="innocent">Innocent</option>
          </select>
        </div>
        {verdict === "guilty" && (
          <>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Punishment Title</label>
              <input
                className={styles.formInput}
                value={punishmentTitle}
                onChange={(e) => setPunishmentTitle(e.target.value)}
                placeholder="e.g. Imprisonment, Fine"
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Punishment Description</label>
              <textarea
                className={styles.formTextarea}
                value={punishmentDesc}
                onChange={(e) => setPunishmentDesc(e.target.value)}
                placeholder="Sentencing details..."
              />
            </div>
          </>
        )}
        <div className={styles.modalActions}>
          <button className={styles.btnDefault} onClick={onClose} type="button">Cancel</button>
          <button
            className={verdict === "guilty" ? styles.btnDanger : styles.btnPrimary}
            onClick={handleSubmit}
            disabled={actions.createTrial.isPending}
            type="button"
          >
            {actions.createTrial.isPending ? "Recording…" : `Record: ${verdict}`}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bail Form Modal
// ---------------------------------------------------------------------------

function BailFormModal({
  suspect,
  caseId,
  onClose,
  onSuccess,
  onError,
}: {
  suspect: Suspect;
  caseId: number;
  onClose: () => void;
  onSuccess: () => void;
  onError: (msg: string) => void;
}) {
  const actions = useSuspectActions(suspect.id, caseId);
  const [amount, setAmount] = useState("");
  const [conditions, setConditions] = useState("");

  const handleSubmit = async () => {
    try {
      await actions.createBail.mutateAsync({
        case: caseId,
        amount: Number(amount),
        conditions: conditions.trim() || undefined,
      });
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to set bail");
    }
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h3>Set Bail — {suspect.full_name}</h3>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>Amount (Rials) *</label>
          <input
            className={styles.formInput}
            type="number"
            min={0}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            placeholder="Bail amount in Rials"
            autoFocus
          />
        </div>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>Conditions</label>
          <textarea
            className={styles.formTextarea}
            value={conditions}
            onChange={(e) => setConditions(e.target.value)}
            placeholder="Bail conditions..."
          />
        </div>
        <div className={styles.modalActions}>
          <button className={styles.btnDefault} onClick={onClose} type="button">Cancel</button>
          <button
            className={styles.btnPrimary}
            onClick={handleSubmit}
            disabled={!amount || Number(amount) <= 0 || actions.createBail.isPending}
            type="button"
          >
            {actions.createBail.isPending ? "Setting…" : "Set Bail"}
          </button>
        </div>
      </div>
    </div>
  );
}
