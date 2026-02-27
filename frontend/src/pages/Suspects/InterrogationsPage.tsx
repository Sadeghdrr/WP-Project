/**
 * InterrogationsPage — View all interrogations for suspects in a case,
 * with the ability to create new interrogation records.
 *
 * Route: /cases/:caseId/interrogations
 */

import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useCaseSuspects } from "../../hooks/useSuspects";
import { useCaseDetail } from "../../hooks/useCases";
import { useSuspectActions } from "../../hooks/useSuspects";
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

export default function InterrogationsPage() {
  const { caseId } = useParams();
  const cId = caseId ? Number(caseId) : undefined;
  const { data: suspects, isLoading, error, refetch } = useCaseSuspects(cId);
  const { data: caseData } = useCaseDetail(cId);
  const { permissionSet } = useAuth();

  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [selectedSuspect, setSelectedSuspect] = useState<Suspect | null>(null);

  const canInterrogate = permissionSet.has("suspects.can_conduct_interrogation");

  // Filter suspects under interrogation
  const interrogatableSuspects = suspects?.filter(
    (s) => s.status === "under_interrogation",
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
          <h1>Interrogations — Case #{cId}{caseData ? `: ${caseData.title}` : ""}</h1>
          <div className={styles.headerMeta}>
            <span className={`${styles.badge} ${styles.badgeBlue}`}>
              {interrogatableSuspects.length} suspect{interrogatableSuspects.length !== 1 ? "s" : ""} ready
            </span>
          </div>
        </div>
      </div>

      {/* Suspects ready for interrogation */}
      {interrogatableSuspects.length === 0 ? (
        <EmptyState
          heading="No Pending Interrogations"
          message="No suspects are currently under interrogation for this case. Suspects must be arrested and transitioned to interrogation status first."
        />
      ) : (
        <div className={`${styles.section} ${styles.fullWidth}`}>
          <h2>Suspects Under Interrogation</h2>
          <table className={styles.subTable}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {interrogatableSuspects.map((s) => (
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
                    {canInterrogate && (
                      <button
                        className={`${styles.btnPrimary} ${styles.btnSmall}`}
                        onClick={() => setSelectedSuspect(s)}
                        type="button"
                      >
                        Record Interrogation
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* All suspects overview */}
      {suspects && suspects.length > 0 && (
        <div className={`${styles.section} ${styles.fullWidth}`} style={{ marginTop: "1.5rem" }}>
          <h2>All Suspects ({suspects.length})</h2>
          <table className={styles.subTable}>
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {suspects.map((s) => (
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

      {/* Interrogation form modal */}
      {selectedSuspect && cId && (
        <InterrogationFormModal
          suspect={selectedSuspect}
          caseId={cId}
          onClose={() => setSelectedSuspect(null)}
          onSuccess={() => {
            setSelectedSuspect(null);
            setToast({ message: "Interrogation recorded successfully", type: "success" });
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
// Interrogation Form Modal
// ---------------------------------------------------------------------------

function InterrogationFormModal({
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
  const [detScore, setDetScore] = useState(5);
  const [sgtScore, setSgtScore] = useState(5);
  const [notes, setNotes] = useState("");

  const handleSubmit = async () => {
    try {
      await actions.createInterrogation.mutateAsync({
        case: caseId,
        detective_guilt_score: detScore,
        sergeant_guilt_score: sgtScore,
        notes: notes.trim() || undefined,
      });
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to record interrogation");
    }
  };

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h3>Interrogation — {suspect.full_name}</h3>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
          <div className={styles.formGroup}>
            <label className={styles.formLabel}>Detective Guilt Score (1–10) *</label>
            <input
              className={styles.scoreInput}
              type="number"
              min={1}
              max={10}
              value={detScore}
              onChange={(e) => setDetScore(Number(e.target.value))}
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.formLabel}>Sergeant Guilt Score (1–10) *</label>
            <input
              className={styles.scoreInput}
              type="number"
              min={1}
              max={10}
              value={sgtScore}
              onChange={(e) => setSgtScore(Number(e.target.value))}
            />
          </div>
        </div>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>Notes</label>
          <textarea
            className={styles.formTextarea}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Interrogation observations..."
          />
        </div>
        <div className={styles.modalActions}>
          <button className={styles.btnDefault} onClick={onClose} type="button">Cancel</button>
          <button
            className={styles.btnPrimary}
            onClick={handleSubmit}
            disabled={detScore < 1 || detScore > 10 || sgtScore < 1 || sgtScore > 10 || actions.createInterrogation.isPending}
            type="button"
          >
            {actions.createInterrogation.isPending ? "Recording…" : "Record Interrogation"}
          </button>
        </div>
      </div>
    </div>
  );
}
