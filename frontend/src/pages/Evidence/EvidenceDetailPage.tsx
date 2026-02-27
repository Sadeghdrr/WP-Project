import { useState, useCallback, useRef } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { Skeleton, ErrorState, MediaViewer } from "../../components/ui";
import {
  useEvidenceDetail,
  useChainOfCustody,
  useEvidenceActions,
} from "../../hooks/useEvidence";
import {
  EVIDENCE_TYPE_LABELS,
  EVIDENCE_TYPE_COLORS,
  EVIDENCE_TYPE_ICONS,
  FILE_TYPE_LABELS,
} from "../../lib/evidenceHelpers";
import { useAuth } from "../../auth";
import type { Evidence, BiologicalEvidence } from "../../types";
import css from "./EvidenceDetailPage.module.css";

const COLOR_CSS: Record<string, string> = {
  blue: css.badgeBlue,
  red: css.badgeRed,
  amber: css.badgeAmber,
  purple: css.badgePurple,
  gray: css.badgeGray,
};

/**
 * Evidence detail page — shows full info for a single evidence item.
 *
 * Features:
 * - Type-specific fields
 * - File attachments with upload
 * - Coroner verification panel (biological evidence)
 * - Chain-of-custody timeline
 * - Delete action
 */
export default function EvidenceDetailPage() {
  const { caseId, evidenceId } = useParams<{
    caseId: string;
    evidenceId: string;
  }>();
  const navigate = useNavigate();
  const numericId = evidenceId ? Number(evidenceId) : undefined;
  const { permissionSet } = useAuth();

  const {
    data: evidence,
    isLoading,
    isError,
    error,
    refetch,
  } = useEvidenceDetail(numericId);

  const { data: custodyLogs } = useChainOfCustody(numericId);
  const actions = useEvidenceActions();

  // Toast state
  const [toast, setToast] = useState<{
    msg: string;
    variant: "success" | "error";
  } | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout>>();

  const showToast = useCallback(
    (msg: string, variant: "success" | "error" = "success") => {
      if (toastTimer.current) clearTimeout(toastTimer.current);
      setToast({ msg, variant });
      toastTimer.current = setTimeout(() => setToast(null), 4000);
    },
    [],
  );

  // ── Verification form state (biological only) ──────────────
  const [forensicResult, setForensicResult] = useState("");
  const [verifyNotes, setVerifyNotes] = useState("");

  const handleVerify = useCallback(
    async (decision: "approve" | "reject") => {
      if (!numericId) return;
      try {
        await actions.verifyEvidence.mutateAsync({
          id: numericId,
          data: {
            decision,
            forensic_result: forensicResult,
            notes: verifyNotes,
          },
        });
        showToast(
          decision === "approve"
            ? "Evidence verified successfully"
            : "Evidence rejected",
        );
        setForensicResult("");
        setVerifyNotes("");
      } catch (err) {
        showToast(
          err instanceof Error ? err.message : "Verification failed",
          "error",
        );
      }
    },
    [numericId, forensicResult, verifyNotes, actions.verifyEvidence, showToast],
  );

  // ── File upload state ──────────────────────────────────────
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadFileType, setUploadFileType] = useState("image");
  const [uploadCaption, setUploadCaption] = useState("");

  const handleUpload = useCallback(async () => {
    if (!numericId || !uploadFile) return;
    try {
      await actions.uploadFile.mutateAsync({
        evidenceId: numericId,
        file: uploadFile,
        fileType: uploadFileType,
        caption: uploadCaption,
      });
      showToast("File uploaded successfully");
      setUploadFile(null);
      setUploadCaption("");
    } catch (err) {
      showToast(
        err instanceof Error ? err.message : "Upload failed",
        "error",
      );
    }
  }, [
    numericId,
    uploadFile,
    uploadFileType,
    uploadCaption,
    actions.uploadFile,
    showToast,
  ]);

  // ── Edit mode ───────────────────────────────────────────────
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const startEditing = useCallback(() => {
    if (!evidence) return;
    setEditTitle(evidence.title);
    setEditDescription(evidence.description);
    setIsEditing(true);
  }, [evidence]);

  const handleEditSave = useCallback(async () => {
    if (!numericId) return;
    try {
      await actions.updateEvidence.mutateAsync({
        id: numericId,
        data: {
          title: editTitle.trim(),
          description: editDescription.trim(),
        },
      });
      showToast("Evidence updated successfully");
      setIsEditing(false);
    } catch (err) {
      showToast(
        err instanceof Error ? err.message : "Update failed",
        "error",
      );
    }
  }, [numericId, editTitle, editDescription, actions.updateEvidence, showToast]);

  // ── Delete ─────────────────────────────────────────────────
  const handleDelete = useCallback(async () => {
    if (!numericId) return;
    if (!window.confirm("Are you sure you want to delete this evidence?"))
      return;
    try {
      await actions.deleteEvidence.mutateAsync(numericId);
      showToast("Evidence deleted");
      navigate(`/cases/${caseId}/evidence`);
    } catch (err) {
      showToast(
        err instanceof Error ? err.message : "Delete failed",
        "error",
      );
    }
  }, [numericId, caseId, navigate, actions.deleteEvidence, showToast]);

  // ── Loading / Error ────────────────────────────────────────
  if (isLoading) {
    return (
      <div className={css.container}>
        <Skeleton style={{ width: "30%", height: "1.5rem", marginBottom: "1rem" }} />
        <Skeleton style={{ width: "100%", height: "12rem", marginBottom: "1rem" }} />
        <Skeleton style={{ width: "100%", height: "8rem" }} />
      </div>
    );
  }

  if (isError || !evidence) {
    return (
      <div className={css.container}>
        <ErrorState
          title="Failed to load evidence"
          message={error?.message ?? "Evidence not found"}
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const typeColor =
    EVIDENCE_TYPE_COLORS[evidence.evidence_type] ?? "gray";
  const isBiological = evidence.evidence_type === "biological";
  const bioEvidence = isBiological
    ? (evidence as BiologicalEvidence)
    : null;
  const canVerify =
    isBiological &&
    !bioEvidence?.is_verified &&
    permissionSet.has("evidence.can_verify_evidence");

  return (
    <div className={css.container}>
      {/* Back link */}
      <Link to={`/cases/${caseId}/evidence`} className={css.backLink}>
        ← Back to Evidence List
      </Link>

      {/* Header */}
      <div className={css.headerRow}>
        <h1>
          {EVIDENCE_TYPE_ICONS[evidence.evidence_type] ?? "📦"}{" "}
          {evidence.title}
        </h1>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
          <div className={css.badges}>
            <span
              className={`${css.badge} ${COLOR_CSS[typeColor] ?? css.badgeGray}`}
            >
              {evidence.evidence_type_display ??
                EVIDENCE_TYPE_LABELS[evidence.evidence_type]}
            </span>
            {isBiological && (
              <span
                className={`${css.badge} ${
                  bioEvidence?.is_verified ? css.badgeGreen : css.badgeAmber
                }`}
              >
                {bioEvidence?.is_verified ? "Verified" : "Pending Verification"}
              </span>
            )}
          </div>
          {permissionSet.has("evidence.change_evidence") && (
            <div style={{ display: "flex", gap: "0.5rem" }}>
              {!isEditing ? (
                <button className={css.btnEdit} onClick={startEditing} type="button">
                  ✏️ Edit
                </button>
              ) : (
                <>
                  <button
                    className={css.btnCancel}
                    onClick={() => setIsEditing(false)}
                    type="button"
                  >
                    Cancel
                  </button>
                  <button
                    className={css.btnEdit}
                    onClick={handleEditSave}
                    disabled={!editTitle.trim() || actions.updateEvidence.isPending}
                    type="button"
                  >
                    {actions.updateEvidence.isPending ? "Saving…" : "Save Changes"}
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Inline Edit Form ──────────────────────────────────── */}
      {isEditing && (
        <div className={css.editForm}>
          <h2>Edit Evidence</h2>
          <div className={css.editField}>
            <label>Title *</label>
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              placeholder="Evidence title"
            />
          </div>
          <div className={css.editField}>
            <label>Description</label>
            <textarea
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              rows={4}
              placeholder="Describe the evidence…"
            />
          </div>
        </div>
      )}

      {/* ── Verification Panel (biological, not yet verified, coroner) ── */}
      {canVerify && (
        <div className={css.verifyPanel}>
          <h2>🧬 Coroner Verification</h2>
          <div className={css.verifyForm}>
            <div className={css.verifyField}>
              <label>Forensic Result</label>
              <textarea
                value={forensicResult}
                onChange={(e) => setForensicResult(e.target.value)}
                placeholder="Enter forensic examination result…"
              />
            </div>
            <div className={css.verifyField}>
              <label>Notes / Rejection Reason</label>
              <textarea
                value={verifyNotes}
                onChange={(e) => setVerifyNotes(e.target.value)}
                placeholder="Additional notes or rejection reason…"
              />
            </div>
            <div className={css.verifyActions}>
              <button
                className={css.btnApprove}
                disabled={actions.verifyEvidence.isPending}
                onClick={() => handleVerify("approve")}
              >
                ✓ Approve
              </button>
              <button
                className={css.btnReject}
                disabled={actions.verifyEvidence.isPending}
                onClick={() => handleVerify("reject")}
              >
                ✗ Reject
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Metadata ───────────────────────────────────────── */}
      <div className={css.section}>
        <h2>Details</h2>
        <div className={css.metaGrid}>
          <div className={css.metaItem}>
            <span className={css.metaLabel}>Case</span>
            <span className={css.metaValue}>
              <Link to={`/cases/${evidence.case}`}>
                Case #{evidence.case}
              </Link>
            </span>
          </div>
          <div className={css.metaItem}>
            <span className={css.metaLabel}>Registered By</span>
            <span className={css.metaValue}>
              {evidence.registered_by_name ??
                `User #${evidence.registered_by}`}
            </span>
          </div>
          <div className={css.metaItem}>
            <span className={css.metaLabel}>Created</span>
            <span className={css.metaValue}>
              {new Date(evidence.created_at).toLocaleString()}
            </span>
          </div>
          <div className={css.metaItem}>
            <span className={css.metaLabel}>Updated</span>
            <span className={css.metaValue}>
              {new Date(evidence.updated_at).toLocaleString()}
            </span>
          </div>
        </div>

        {/* Description */}
        {evidence.description && (
          <>
            <h3>Description</h3>
            <p className={css.description}>{evidence.description}</p>
          </>
        )}

        {/* Type-specific fields */}
        <TypeSpecificDetails evidence={evidence} />
      </div>

      {/* ── Files ──────────────────────────────────────────── */}
      <div className={css.section}>
        <h2>Files & Attachments</h2>
        {evidence.files && evidence.files.length > 0 ? (
          <div className={css.fileGrid}>
            {evidence.files.map((f) => (
              <div key={f.id} className={css.fileCard}>
                <MediaViewer
                  fileUrl={f.file}
                  fileType={f.file_type}
                  fileTypeDisplay={f.file_type_display ?? FILE_TYPE_LABELS[f.file_type]}
                  caption={f.caption}
                />
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            No files attached yet.
          </p>
        )}

        {/* Upload form */}
        <div className={css.uploadForm}>
          <div className={css.uploadField}>
            <label>File</label>
            <input
              type="file"
              onChange={(e) =>
                setUploadFile(e.target.files?.[0] ?? null)
              }
            />
          </div>
          <div className={css.uploadField}>
            <label>Type</label>
            <select
              value={uploadFileType}
              onChange={(e) => setUploadFileType(e.target.value)}
            >
              <option value="image">Image</option>
              <option value="video">Video</option>
              <option value="audio">Audio</option>
              <option value="document">Document</option>
            </select>
          </div>
          <div className={css.uploadField}>
            <label>Caption</label>
            <input
              type="text"
              value={uploadCaption}
              onChange={(e) => setUploadCaption(e.target.value)}
              placeholder="Optional caption"
            />
          </div>
          <button
            className={css.uploadBtn}
            disabled={!uploadFile || actions.uploadFile.isPending}
            onClick={handleUpload}
          >
            {actions.uploadFile.isPending ? "Uploading…" : "Upload"}
          </button>
        </div>
      </div>

      {/* ── Chain of Custody ───────────────────────────────── */}
      <div className={css.section}>
        <h2>Chain of Custody</h2>
        {custodyLogs && custodyLogs.length > 0 ? (
          <div className={css.timeline}>
            {custodyLogs.map((log) => (
              <div key={log.id} className={css.timelineItem}>
                <span className={css.timelineAction}>{log.action}</span>
                <div className={css.timelineMeta}>
                  {log.performer_name ?? `User #${log.performed_by}`} —{" "}
                  {new Date(log.timestamp).toLocaleString()}
                </div>
                {log.details && (
                  <div className={css.timelineNotes}>{log.details}</div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            No custody records yet.
          </p>
        )}
      </div>

      {/* ── Delete action ──────────────────────────────────── */}
      <div style={{ marginTop: "0.5rem" }}>
        <button className={css.deleteBtn} onClick={handleDelete}>
          Delete Evidence
        </button>
      </div>

      {/* Toast */}
      {toast && (
        <div
          className={`${css.toast} ${
            toast.variant === "success" ? css.toastSuccess : css.toastError
          }`}
        >
          {toast.msg}
        </div>
      )}
    </div>
  );
}

// ── Type-specific field rendering ──────────────────────────────────────

function TypeSpecificDetails({ evidence }: { evidence: Evidence }) {
  switch (evidence.evidence_type) {
    case "testimony":
      return (
        <>
          <h3>Statement Transcript</h3>
          <p className={css.description}>
            {evidence.statement_text || "No transcript provided."}
          </p>
        </>
      );

    case "biological":
      return (
        <>
          <h3>Forensic Result</h3>
          <p className={css.description}>
            {evidence.forensic_result || "Awaiting forensic examination."}
          </p>
          {evidence.verified_by_name && (
            <p style={{ fontSize: "0.85rem", marginTop: "0.25rem" }}>
              <strong>Verified by:</strong> {evidence.verified_by_name}
            </p>
          )}
        </>
      );

    case "vehicle":
      return (
        <div className={css.metaGrid} style={{ marginTop: "0.75rem" }}>
          <div className={css.metaItem}>
            <span className={css.metaLabel}>Vehicle Model</span>
            <span className={css.metaValue}>{evidence.vehicle_model}</span>
          </div>
          <div className={css.metaItem}>
            <span className={css.metaLabel}>Color</span>
            <span className={css.metaValue}>{evidence.color}</span>
          </div>
          {evidence.license_plate && (
            <div className={css.metaItem}>
              <span className={css.metaLabel}>License Plate</span>
              <span className={css.metaValue}>{evidence.license_plate}</span>
            </div>
          )}
          {evidence.serial_number && (
            <div className={css.metaItem}>
              <span className={css.metaLabel}>Serial Number</span>
              <span className={css.metaValue}>{evidence.serial_number}</span>
            </div>
          )}
        </div>
      );

    case "identity": {
      const entries = Object.entries(evidence.document_details ?? {});
      return (
        <>
          <div className={css.metaGrid} style={{ marginTop: "0.75rem" }}>
            <div className={css.metaItem}>
              <span className={css.metaLabel}>Document Owner</span>
              <span className={css.metaValue}>
                {evidence.owner_full_name}
              </span>
            </div>
          </div>
          {entries.length > 0 && (
            <>
              <h3>Document Details</h3>
              <table className={css.kvTable}>
                <tbody>
                  {entries.map(([key, val]) => (
                    <tr key={key}>
                      <td>{key}</td>
                      <td>{val}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </>
      );
    }

    case "other":
    default:
      return null;
  }
}
