/**
 * PinEntityModal — dialog for pinning a case, evidence, or suspect to the board.
 *
 * Fetches the lists of entities relevant to the current case and lets the user
 * pick one to add as a BoardItem.
 *
 * The backend accepts any ContentType from:
 *   cases.case, suspects.suspect, evidence.evidence,
 *   evidence.testimonyevidence, evidence.biologicalevidence,
 *   evidence.vehicleevidence, evidence.identityevidence, board.boardnote
 *
 * We offer two categories here:
 *   1. Evidence linked to this case
 *   2. Suspects linked to this case
 *
 * Notes are created through the sidebar (the backend auto-pins them).
 */

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../api/client";
import { API } from "../../api/endpoints";
import css from "./DetectiveBoardPage.module.css";
import type { BoardItem } from "../../types/board";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PinnableEntity {
  content_type_id: number;
  object_id: number;
  label: string;
  model: string;
}

interface Props {
  caseId: number;
  existingItems: BoardItem[];
  onPin: (entity: { content_type_id: number; object_id: number }) => void;
  isPinning: boolean;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PinEntityModal({
  caseId,
  existingItems,
  onPin,
  isPinning,
  onClose,
}: Props) {
  const [entities, setEntities] = useState<PinnableEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<PinnableEntity | null>(null);

  // Fetch available entities
  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      const items: PinnableEntity[] = [];

      try {
        // 1) Evidence for this case
        const evRes = await apiGet<
          | Array<{ id: number; evidence_type: string; description?: string; content_type_id?: number }>
          | { results: Array<{ id: number; evidence_type: string; description?: string; content_type_id?: number }> }
        >(`${API.EVIDENCE}?case=${caseId}`);
        if (evRes.ok) {
          const evList = Array.isArray(evRes.data)
            ? evRes.data
            : evRes.data.results ?? [];
          for (const ev of evList) {
            // The base Evidence model content_type is used for generic evidence;
            // specific subtypes use their own CT, but the board serializer
            // resolves it via GenericObjectRelatedField. We use the base Evidence
            // CT here since the backend maps it.
            items.push({
              content_type_id: ev.content_type_id ?? 0,
              object_id: ev.id,
              label: `${ev.evidence_type ?? "Evidence"} — ${ev.description?.substring(0, 60) || `#${ev.id}`}`,
              model: "evidence",
            });
          }
        }

        // 2) Suspects for this case
        const susRes = await apiGet<
          | Array<{ id: number; full_name: string; national_id: string; content_type_id?: number }>
          | { results: Array<{ id: number; full_name: string; national_id: string; content_type_id?: number }> }
        >(`${API.SUSPECTS}?case=${caseId}`);
        if (susRes.ok) {
          const susList = Array.isArray(susRes.data)
            ? susRes.data
            : susRes.data.results ?? [];
          for (const s of susList) {
            items.push({
              content_type_id: s.content_type_id ?? 0,
              object_id: s.id,
              label: `${s.full_name} (${s.national_id})`,
              model: "suspect",
            });
          }
        }

        if (!cancelled) setEntities(items);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load entities");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  // Filter out entities already on the board
  const alreadyPinned = new Set(
    existingItems.map((i) => `${i.content_type}:${i.object_id}`),
  );

  const available = entities.filter(
    (e) => !alreadyPinned.has(`${e.content_type_id}:${e.object_id}`),
  );

  const handlePin = useCallback(() => {
    if (!selected) return;
    onPin({
      content_type_id: selected.content_type_id,
      object_id: selected.object_id,
    });
  }, [selected, onPin]);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).dataset.backdrop) onClose();
    },
    [onClose],
  );

  return (
    <div
      className={css.modalBackdrop}
      data-backdrop="1"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label="Pin entity to board"
    >
      <div className={css.modal}>
        <h2 className={css.modalTitle}>Pin Entity to Board</h2>

        {loading && <p className={css.emptyHint}>Loading available entities…</p>}
        {error && <p className={css.errorInline}>{error}</p>}

        {!loading && available.length === 0 && !error && (
          <p className={css.emptyHint}>
            No un-pinned evidence or suspects found for this case.
          </p>
        )}

        {!loading &&
          available.map((e) => (
            <div
              key={`${e.model}:${e.object_id}`}
              className={
                selected === e ? css.entityOptionSelected : css.entityOption
              }
              onClick={() => setSelected(e)}
              role="button"
              tabIndex={0}
              onKeyDown={(ev) => ev.key === "Enter" && setSelected(e)}
            >
              {e.model === "suspect" ? "🔍 " : "🔬 "}
              {e.label}
            </div>
          ))}

        <div className={css.modalFooter}>
          <button
            type="button"
            className={css.btn}
            onClick={onClose}
            disabled={isPinning}
          >
            Cancel
          </button>
          <button
            type="button"
            className={css.btnPrimary}
            onClick={handlePin}
            disabled={!selected || isPinning}
          >
            {isPinning ? "Pinning…" : "Pin to Board"}
          </button>
        </div>
      </div>
    </div>
  );
}
