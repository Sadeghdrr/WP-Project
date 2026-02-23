/**
 * BoardToolbar — top toolbar for the detective board.
 *
 * Actions:
 *  - Add evidence/suspect/case item
 *  - Add sticky note
 *  - Toggle connection mode
 *  - Export as image
 *  - Zoom controls
 *  - Save indicator
 */
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface BoardToolbarProps {
  boardId: number;
  caseId: number;
  savePending: boolean;
  connectionMode: boolean;
  onAddItemClick: () => void;
  onAddNoteClick: () => void;
  onToggleConnectionMode: () => void;
  onCancelConnection: () => void;
  onExport: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomReset: () => void;
  zoom: number;
}

export function BoardToolbar({
  caseId,
  savePending,
  connectionMode,
  onAddItemClick,
  onAddNoteClick,
  onToggleConnectionMode,
  onCancelConnection,
  onExport,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  zoom,
}: BoardToolbarProps) {
  return (
    <div className="board-toolbar">
      <div className="board-toolbar__left">
        <h2 className="board-toolbar__title">
          Detective Board — Case #{caseId}
        </h2>
        {savePending && (
          <Badge variant="warning" size="sm">
            Saving…
          </Badge>
        )}
        {!savePending && (
          <Badge variant="success" size="sm">
            Saved
          </Badge>
        )}
      </div>

      <div className="board-toolbar__center">
        <Button size="sm" variant="primary" onClick={onAddItemClick}>
          + Pin Item
        </Button>
        <Button size="sm" variant="secondary" onClick={onAddNoteClick}>
          + Note
        </Button>
        {connectionMode ? (
          <Button size="sm" variant="danger" onClick={onCancelConnection}>
            Cancel Connection
          </Button>
        ) : (
          <Button
            size="sm"
            variant="secondary"
            onClick={onToggleConnectionMode}
          >
            🔗 Draw Connection
          </Button>
        )}
      </div>

      <div className="board-toolbar__right">
        <div className="board-toolbar__zoom">
          <Button size="sm" variant="secondary" onClick={onZoomOut}>
            −
          </Button>
          <span
            className="board-toolbar__zoom-label"
            onClick={onZoomReset}
            title="Reset zoom"
          >
            {Math.round(zoom * 100)}%
          </span>
          <Button size="sm" variant="secondary" onClick={onZoomIn}>
            +
          </Button>
        </div>
        <Button size="sm" variant="secondary" onClick={onExport}>
          📷 Export
        </Button>
      </div>
    </div>
  );
}
