import { useEffect, useRef, useState } from "react";
import type { FormEventHandler } from "react";
import type { Note, NoteDraft } from "../types/note";

type NoteEditorProps = {
  note: Note | null;
  isNew: boolean;
  draft: NoteDraft;
  saving: boolean;
  summarizing: boolean;
  hasUnsavedChanges: boolean;
  error: string;
  onDraftChange: (draft: NoteDraft) => void;
  onSave: FormEventHandler<HTMLFormElement>;
  onDelete: () => void;
  onSummarize: () => void;
  onCreate: () => void;
};

export function NoteEditor({
  note,
  isNew,
  draft,
  saving,
  summarizing,
  hasUnsavedChanges,
  error,
  onDraftChange,
  onSave,
  onDelete,
  onSummarize,
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
                    className="outline-button"
                    type="button"
                    onClick={onSummarize}
                    disabled={saving || summarizing || hasUnsavedChanges}
                    title={
                      hasUnsavedChanges
                        ? "Save your changes before summarizing"
                        : "Generate an AI summary of this saved note"
                    }
                  >
                    {summarizing ? "Summarizing…" : "Summarize note"}
                  </button>
                  <button
                    className="outline-button danger-button"
                    type="button"
                    onClick={onDelete}
                    disabled={saving || summarizing}
                  >
                    Delete
                  </button>
                </>
              )}
              <button
                className="save-button"
                type="submit"
                form="note-form"
                disabled={!canSave || saving || summarizing}
              >
                {saving ? "Saving…" : "Save note"}
              </button>
            </div>
          </div>
          <form id="note-form" className="note-form" onSubmit={onSave}>
            <input
              className="title-input"
              aria-label="Note title"
              maxLength={70}
              aria-describedby={draft.title.length >= 70 ? "title-limit" : undefined}
              placeholder="Untitled note"
              value={draft.title}
              onChange={(event) =>
                onDraftChange({ ...draft, title: event.target.value })
              }
              required
            />
            {draft.title.length >= 70 && (
              <span id="title-limit" className="limit-hint" role="status">
                Title limit reached (70 characters).
              </span>
            )}
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
              maxLength={5000}
              aria-describedby={draft.content.length >= 5000 ? "content-limit" : undefined}
              placeholder="Start writing…"
              value={draft.content}
              onChange={(event) =>
                onDraftChange({ ...draft, content: event.target.value })
              }
              required
            />
            {draft.content.length >= 5000 && (
              <span id="content-limit" className="limit-hint" role="status">
                Note limit reached (5,000 characters).
              </span>
            )}
          </form>
          {note?.summary && !hasUnsavedChanges && (
            <section className="note-summary" aria-label="AI summary">
              <h3>AI summary</h3>
              <p>{note.summary}</p>
            </section>
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