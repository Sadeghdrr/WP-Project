/**
 * SuspectsPage — List suspects for a case with create form & inline actions.
 *
 * Route: /cases/:caseId/suspects
 */

import { useState, useCallback, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useCaseSuspects, useCreateSuspect } from "../../hooks/useSuspects";
import { useCaseDetail } from "../../hooks/useCases";
import { useAuth } from "../../auth/useAuth";
import { Skeleton, ErrorState, EmptyState } from "../../components/ui";
import {
  SUSPECT_STATUS_LABELS,
  SUSPECT_STATUS_COLORS,
  APPROVAL_STATUS_LABELS,
  APPROVAL_STATUS_COLORS,
} from "../../lib/suspectWorkflow";
import type { SuspectStatus, SergeantApprovalStatus } from "../../types";
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

export default function SuspectsPage() {
  const { caseId } = useParams();
  const cId = caseId ? Number(caseId) : undefined;
  const { data: suspects, isLoading, error, refetch } = useCaseSuspects(cId);
  const { data: caseData } = useCaseDetail(cId);
  const { permissionSet } = useAuth();

  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  const canIdentify = permissionSet.has("suspects.can_identify_suspect");

  if (isLoading) {
    return (
      <div className={styles.container}>
        <Skeleton width={120} />
        <Skeleton variant="rect" height={32} />
        <Skeleton count={5} />
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
          <h1>Suspects — Case #{cId}{caseData ? `: ${caseData.title}` : ""}</h1>
          <div className={styles.headerMeta}>
            <span className={`${styles.badge} ${styles.badgeBlue}`}>
              {suspects?.length ?? 0} suspect{(suspects?.length ?? 0) !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
        {canIdentify && caseData?.status === "investigation" && (
          <button
            className={styles.btnPrimary}
            onClick={() => setShowCreateForm(true)}
            type="button"
          >
            + Identify Suspect
          </button>
        )}
      </div>

      {/* Create suspect form */}
      {showCreateForm && cId && (
        <CreateSuspectForm
          caseId={cId}
          onClose={() => setShowCreateForm(false)}
          onSuccess={() => {
            setShowCreateForm(false);
            setToast({ message: "Suspect identified successfully", type: "success" });
            refetch();
          }}
          onError={(msg) => setToast({ message: msg, type: "error" })}
        />
      )}

      {/* Suspects table */}
      {!suspects || suspects.length === 0 ? (
        <EmptyState
          heading="No Suspects"
          message="No suspects have been identified for this case yet."
        />
      ) : (
        <div className={`${styles.section} ${styles.fullWidth}`}>
          <table className={styles.subTable}>
            <thead>
              <tr>
                <th>Name</th>
                <th>National ID</th>
                <th>Status</th>
                <th>Approval</th>
                <th>Wanted Since</th>
                <th>Days Wanted</th>
              </tr>
            </thead>
            <tbody>
              {suspects.map((s) => (
                <tr key={s.id} className={styles.clickableRow}>
                  <td>
                    <Link
                      to={`/cases/${cId}/suspects/${s.id}`}
                      style={{ color: "var(--color-primary, #4f46e5)", fontWeight: 600, textDecoration: "none" }}
                    >
                      {s.full_name}
                    </Link>
                  </td>
                  <td>{s.national_id || "—"}</td>
                  <td><SuspectStatusBadge status={s.status} /></td>
                  <td><ApprovalBadge status={s.sergeant_approval_status} /></td>
                  <td>{new Date(s.wanted_since).toLocaleDateString()}</td>
                  <td>{s.days_wanted}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Create Suspect Form
// ---------------------------------------------------------------------------

function CreateSuspectForm({
  caseId,
  onClose,
  onSuccess,
  onError,
}: {
  caseId: number;
  onClose: () => void;
  onSuccess: () => void;
  onError: (msg: string) => void;
}) {
  const createMutation = useCreateSuspect();
  const [fullName, setFullName] = useState("");
  const [nationalId, setNationalId] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      try {
        await createMutation.mutateAsync({
          case: caseId,
          full_name: fullName.trim(),
          national_id: nationalId.trim() || undefined,
          phone_number: phone.trim() || undefined,
          address: address.trim() || undefined,
          description: description.trim() || undefined,
        });
        onSuccess();
      } catch (err) {
        onError(err instanceof Error ? err.message : "Failed to create suspect");
      }
    },
    [caseId, fullName, nationalId, phone, address, description, createMutation, onSuccess, onError],
  );

  return (
    <div className={styles.section} style={{ marginBottom: "1.5rem" }}>
      <h2>Identify New Suspect</h2>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>Full Name *</label>
          <input
            className={styles.formInput}
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
          <div className={styles.formGroup}>
            <label className={styles.formLabel}>National ID</label>
            <input
              className={styles.formInput}
              type="text"
              value={nationalId}
              onChange={(e) => setNationalId(e.target.value)}
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.formLabel}>Phone</label>
            <input
              className={styles.formInput}
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
        </div>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>Address</label>
          <input
            className={styles.formInput}
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
          />
        </div>
        <div className={styles.formGroup}>
          <label className={styles.formLabel}>Description</label>
          <textarea
            className={styles.formTextarea}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className={styles.actionButtons}>
          <button type="button" className={styles.btnDefault} onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className={styles.btnPrimary}
            disabled={!fullName.trim() || createMutation.isPending}
          >
            {createMutation.isPending ? "Creating…" : "Identify Suspect"}
          </button>
        </div>
      </form>
    </div>
  );
}
