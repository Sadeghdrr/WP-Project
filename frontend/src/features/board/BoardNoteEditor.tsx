/**
 * BoardNoteEditor — inline form for creating / editing board sticky notes.
 *
 * When `note` is provided, the form is in edit mode.
 * Otherwise it's a create form.
 *
 * Notes are auto-pinned to the canvas by the backend (it auto-creates
 * a BoardItem referencing the note via GenericForeignKey).
 */
import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/Button';
import type { BoardNote } from '@/types/board.types';

interface BoardNoteEditorProps {
  note?: BoardNote;
  open: boolean;
  onClose: () => void;
  onSave: (title: string, content: string) => void;
  onDelete?: (noteId: number) => void;
  saving: boolean;
}

export function BoardNoteEditor({
  note,
  open,
  onClose,
  onSave,
  onDelete,
  saving,
}: BoardNoteEditorProps) {
  const [title, setTitle] = useState(note?.title ?? '');
  const [content, setContent] = useState(note?.content ?? '');

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!title.trim()) return;
      onSave(title.trim(), content.trim());
    },
    [title, content, onSave],
  );

  const handleDelete = useCallback(() => {
    if (note && onDelete) {
      onDelete(note.id);
    }
  }, [note, onDelete]);

  if (!open) return null;

  const isEdit = !!note;

  return (
    <div className="board-note-editor">
      <div className="board-note-editor__overlay" onClick={onClose} />
      <form className="board-note-editor__form" onSubmit={handleSubmit}>
        <h3 className="board-note-editor__heading">
          {isEdit ? 'Edit Note' : 'New Sticky Note'}
        </h3>

        <label className="board-note-editor__label" htmlFor="note-title">
          Title
        </label>
        <input
          id="note-title"
          className="board-note-editor__input"
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Note title"
          autoFocus
          required
        />

        <label className="board-note-editor__label" htmlFor="note-content">
          Content
        </label>
        <textarea
          id="note-content"
          className="board-note-editor__textarea"
          rows={4}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Write your note…"
        />

        <div className="board-note-editor__actions">
          <Button
            type="submit"
            size="sm"
            variant="primary"
            loading={saving}
            disabled={!title.trim()}
          >
            {isEdit ? 'Update' : 'Create & Pin'}
          </Button>
          {isEdit && onDelete && (
            <Button
              type="button"
              size="sm"
              variant="danger"
              onClick={handleDelete}
            >
              Delete
            </Button>
          )}
          <Button type="button" size="sm" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}
