import { useEffect, useRef, useState } from "react";
import type { FormEventHandler } from "react";
import type { Note, NoteDraft } from "../types/note";

type NoteEditorProps = {
  note: Note | null;
  isNew: boolean;
  draft: NoteDraft;
  saving: boolean;
  enriching: boolean;
  hasUnsavedChanges: boolean;
  error: string;
  onDraftChange: (draft: NoteDraft) => void;
  onSave: FormEventHandler<HTMLFormElement>;
  onDelete: () => void;
  onEnrich: () => void;
  onCreate: () => void;
};

export function NoteEditor({
  note,
  isNew,
  draft,
  saving,
  enriching,
  hasUnsavedChanges,
  error,
  onDraftChange,
  onSave,
  onDelete,
  onEnrich,
  onCreate,
}: NoteEditorProps) {
  const hasEditor = isNew || note !== null;
  const canSave =
    draft.title.trim().length > 0 && draft.content.trim().length > 0;
  const [justSaved, setJustSaved] = useState(false);
  const wasSaving = useRef(false);

  useEffect(() => {
    if (wasSaving.current && !saving && !error) {
      setJustSaved(true);
      const timer = window.setTimeout(() => setJustSaved(false), 2500);
      wasSaving.current = false;
      return () => window.clearTimeout(timer);
    }
    wasSaving.current = saving;
  }, [saving, error]);

  const showUnsaved = hasUnsavedChanges || (isNew && (draft.title || draft.content));
  const status = showUnsaved ? "Unsaved changes" : justSaved ? "Saved" : "";

  return (
    <section className="editor-panel" aria-label="Note editor">
      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}
      {hasEditor ? (
        <>
          <div className="editor-toolbar">
            <span>{isNew ? "NEW NOTE" : `NOTE  /  ${note?.id}`}</span>
            <div className="toolbar-actions">
              {status && (
                <span
                  className={`save-status${showUnsaved ? " is-unsaved" : ""}`}
                  role="status"
                >
                  {status}
                </span>
              )}
              {note && (
                <>
                  <button
                    className="text-button enrich-button"
                    type="button"
                    onClick={onEnrich}
                    disabled={saving || enriching || hasUnsavedChanges}
                    title={
                      hasUnsavedChanges
                        ? "Save your changes before enriching"
                        : "Generate a summary and suggested tags"
                    }
                  >
                    {enriching ? "Enriching…" : "Enrich with AI"}
                  </button>
                  <button
                    className="text-button delete-button"
                    type="button"
                    onClick={onDelete}
                    disabled={saving || enriching}
                  >
                    Delete
                  </button>
                </>
              )}
              <button
                className="save-button"
                type="submit"
                form="note-form"
                disabled={!canSave || saving || enriching}
              >
                {saving ? "Saving…" : "Save note"}
              </button>
            </div>
          </div>
          <form id="note-form" className="note-form" onSubmit={onSave}>
            <input
              className="title-input"
              aria-label="Note title"
              placeholder="Untitled note"
              value={draft.title}
              onChange={(event) =>
                onDraftChange({ ...draft, title: event.target.value })
              }
              required
            />
            <div className="editor-meta">
              <span>
                {note
                  ? `Updated ${new Date(note.updatedAt).toLocaleString()}`
                  : "A new note"}
              </span>
              <span>{draft.content.length} characters</span>
            </div>
            <textarea
              aria-label="Note content"
              placeholder="Start writing…"
              value={draft.content}
              onChange={(event) =>
                onDraftChange({ ...draft, content: event.target.value })
              }
              required
            />
          </form>
          {note && (note.summary || note.tags.length > 0) && (
            <div className="note-extras">
              {note.summary && <p>{note.summary}</p>}
              {note.tags.length > 0 && (
                <div className="tags">
                  {note.tags.map((tag) => (
                    <span key={tag}>{tag}</span>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        <div className="empty-editor">
          <div className="empty-mark" aria-hidden="true">
            ✳
          </div>
          <h2>Your thoughts, gathered.</h2>
          <p>Select a note to read it, or start with a fresh page.</p>
          <button className="new-button" type="button" onClick={onCreate}>
            ＋ New note
          </button>
        </div>
      )}
    </section>
  );
}