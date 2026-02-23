/**
 * BoardAddItemModal — modal for pinning evidence/suspects/cases to the board.
 *
 * Fetches the case's evidence and suspects, lets the user select items
 * to pin onto the board. Items already pinned are greyed out.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Alert } from '@/components/ui/Alert';
import { evidenceApi } from '@/services/api/evidence.api';
import { suspectsApi } from '@/services/api/suspects.api';
import type { BoardItem, BoardItemCreateRequest } from '@/types/board.types';
import type { EvidenceListItem } from '@/types/evidence.types';
import type { SuspectListItem } from '@/types/suspect.types';

interface BoardAddItemModalProps {
  open: boolean;
  onClose: () => void;
  caseId: number;
  existingItems: BoardItem[];
  onAddItem: (data: BoardItemCreateRequest) => void;
  adding: boolean;
}

/** Content type IDs are dynamic per Django installation — we fetch them */
interface PinnableItem {
  content_type_id: number;
  object_id: number;
  display_name: string;
  model: string;
  alreadyPinned: boolean;
}

export function BoardAddItemModal({
  open,
  onClose,
  caseId,
  existingItems,
  onAddItem,
  adding,
}: BoardAddItemModalProps) {
  const [selectedTab, setSelectedTab] = useState<'evidence' | 'suspects'>(
    'evidence',
  );

  const { data: evidenceData, isLoading: evidenceLoading } = useQuery({
    queryKey: ['case-evidence', caseId],
    queryFn: () => evidenceApi.list({ case: caseId }),
    enabled: open,
  });

  const { data: suspectsData, isLoading: suspectsLoading } = useQuery({
    queryKey: ['case-suspects', caseId],
    queryFn: () => suspectsApi.list({ case: caseId }),
    enabled: open,
  });

  const handlePin = (contentTypeId: number, objectId: number) => {
    onAddItem({
      content_object: { content_type_id: contentTypeId, object_id: objectId },
      position_x: 100 + Math.random() * 400,
      position_y: 100 + Math.random() * 300,
    });
  };

  // Build pinnable items list from evidence
  const evidenceItems: PinnableItem[] = (evidenceData?.results ?? []).map(
    (e: EvidenceListItem) => ({
      content_type_id: 0, // Will be resolved by backend via content_object
      object_id: e.id,
      display_name: `${e.title} (${e.evidence_type})`,
      model: e.evidence_type ?? 'evidence',
      alreadyPinned: false,
    }),
  );

  const suspectItems: PinnableItem[] = (suspectsData?.results ?? []).map(
    (s: SuspectListItem) => ({
      content_type_id: 0,
      object_id: s.id,
      display_name: s.full_name ?? `Suspect #${s.id}`,
      model: 'suspect',
      alreadyPinned: false,
    }),
  );

  // Check pinned status by matching object_id (content_type matching
  // is approximate since we don't know exact IDs client-side)
  const markPinned = (items: PinnableItem[]): PinnableItem[] =>
    items.map((it) => ({
      ...it,
      alreadyPinned: existingItems.some(
        (existing) => existing.object_id === it.object_id &&
          existing.content_object_summary?.model === it.model,
      ),
    }));

  const displayItems = selectedTab === 'evidence'
    ? markPinned(evidenceItems)
    : markPinned(suspectItems);
  const isLoading = selectedTab === 'evidence' ? evidenceLoading : suspectsLoading;

  return (
    <Modal open={open} onClose={onClose} title="Pin Item to Board">
      <div className="board-add-modal">
        <div className="board-add-modal__tabs">
          <Button
            size="sm"
            variant={selectedTab === 'evidence' ? 'primary' : 'secondary'}
            onClick={() => setSelectedTab('evidence')}
          >
            Evidence
          </Button>
          <Button
            size="sm"
            variant={selectedTab === 'suspects' ? 'primary' : 'secondary'}
            onClick={() => setSelectedTab('suspects')}
          >
            Suspects
          </Button>
        </div>

        <div className="board-add-modal__info">
          <Alert type="info">
            Select an item to pin it onto the detective board. Items
            already pinned are indicated with a badge.
          </Alert>
        </div>

        {isLoading ? (
          <Skeleton height={200} />
        ) : displayItems.length === 0 ? (
          <p className="board-add-modal__empty">
            No {selectedTab} found for this case.
          </p>
        ) : (
          <ul className="board-add-modal__list">
            {displayItems.map((item) => (
              <li
                key={`${item.model}-${item.object_id}`}
                className={`board-add-modal__item ${item.alreadyPinned ? 'board-add-modal__item--pinned' : ''}`}
              >
                <span className="board-add-modal__item-name">
                  {item.display_name}
                </span>
                {item.alreadyPinned ? (
                  <Badge variant="neutral" size="sm">
                    Pinned
                  </Badge>
                ) : (
                  <Button
                    size="sm"
                    variant="primary"
                    loading={adding}
                    onClick={() =>
                      handlePin(item.content_type_id, item.object_id)
                    }
                  >
                    Pin
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  );
}
