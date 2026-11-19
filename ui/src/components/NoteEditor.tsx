import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { FormEventHandler, ReactNode } from "react";
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
  emptyState?: ReactNode;
  sourcePassages?: string[];
};

const EMPTY_PASSAGES: string[] = [];

function findPassageRanges(
  content: string,
  title: string,
  passages: string[],
): Array<{ start: number; end: number }> {
  let normalized = "";
  const starts: number[] = [];
  const ends: number[] = [];
  let inWhitespace = false;
  for (let index = 0; index < content.length; index += 1) {
    const character = content[index];
    if (/\s/.test(character)) {
      if (normalized && !inWhitespace) {
        normalized += " ";
        starts.push(index);
        ends.push(index + 1);
      } else if (inWhitespace) {
        ends[ends.length - 1] = index + 1;
      }
      inWhitespace = true;
    } else {
      normalized += character;
      starts.push(index);
      ends.push(index + 1);
      inWhitespace = false;
    }
  }

  const ranges = new Map<string, { start: number; end: number }>();
  for (const rawPassage of passages) {
    let passage = rawPassage.trim();
    const titlePrefix = `${title.trim()}\n\n`;
    if (title.trim() && passage.startsWith(titlePrefix)) {
      passage = passage.slice(titlePrefix.length).trim();
    }
    const needle = passage.replace(/\s+/g, " ").trim();
    if (!needle) continue;

    const position = normalized.indexOf(needle);
    if (position < 0) continue;
    const start = starts[position];
    const end = ends[position + needle.length - 1];
    ranges.set(`${start}:${end}`, { start, end });
  }
  const sorted = [...ranges.values()].sort((a, b) => a.start - b.start);
  return sorted.reduce<Array<{ start: number; end: number }>>((merged, range) => {
    const previous = merged[merged.length - 1];
    if (previous && range.start <= previous.end) {
      previous.end = Math.max(previous.end, range.end);
    } else {
      merged.push({ ...range });
    }
    return merged;
  }, []);
}

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
  emptyState = null,
  sourcePassages = EMPTY_PASSAGES,
}: NoteEditorProps) {
  const hasEditor = isNew || note !== null;
  const canSave =
    draft.title.trim().length > 0 && draft.content.trim().length > 0;
  const [justSaved, setJustSaved] = useState(false);
  const wasSaving = useRef(false);
  const contentArea = useRef<HTMLTextAreaElement>(null);
  const overlay = useRef<HTMLPreElement>(null);
  const [showSourceHighlight, setShowSourceHighlight] = useState(false);
  const [isSourceHighlightFading, setIsSourceHighlightFading] = useState(false);
  const ranges = findPassageRanges(
    draft.content,
    note?.title ?? draft.title,
    sourcePassages,
  );

  useEffect(() => {
    if (wasSaving.current && !saving && !error) {
      setJustSaved(true);
      const timer = window.setTimeout(() => setJustSaved(false), 2500);
      wasSaving.current = false;
      return () => window.clearTimeout(timer);
    }
    wasSaving.current = saving;
  }, [saving, error]);

  useLayoutEffect(() => {
    setShowSourceHighlight(ranges.length > 0);
    setIsSourceHighlightFading(false);
    if (!ranges.length) return;

    const first = ranges[0];
    contentArea.current?.focus({ preventScroll: true });
    contentArea.current?.setSelectionRange(first.start, first.start);
    const frame = window.requestAnimationFrame(scrollFirstHighlightToTop);
    let fadeOutTimer: number | undefined;
    const fadeTimer = window.setTimeout(() => {
      setIsSourceHighlightFading(true);
      fadeOutTimer = window.setTimeout(() => setShowSourceHighlight(false), 500);
    }, 3000);
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(fadeTimer);
      if (fadeOutTimer !== undefined) window.clearTimeout(fadeOutTimer);
    };
  }, [note?.id, sourcePassages]);

  function syncOverlayScroll() {
    if (contentArea.current && overlay.current) {
      overlay.current.scrollTop = contentArea.current.scrollTop;
      overlay.current.scrollLeft = contentArea.current.scrollLeft;
    }
  }

  function scrollFirstHighlightToTop() {
    const area = contentArea.current;
    const highlight = overlay.current?.querySelector("mark");
    const highlightOverlay = overlay.current;
    if (!area || !highlight || !highlightOverlay) return;

    const highlightTop =
      highlight.getBoundingClientRect().top -
      highlightOverlay.getBoundingClientRect().top +
      highlightOverlay.scrollTop;
    area.scrollTop = Math.max(0, highlightTop - 4);
    syncOverlayScroll();
  }

  function renderHighlightedContent(): ReactNode[] {
    const pieces: ReactNode[] = [];
    let cursor = 0;
    ranges.forEach((range, index) => {
      pieces.push(draft.content.slice(cursor, range.start));
      pieces.push(
        <mark key={`${range.start}:${index}`} className="source-chunk-highlight">
          {draft.content.slice(range.start, range.end)}
        </mark>,
      );
      cursor = range.end;
    });
    pieces.push(draft.content.slice(cursor));
    return pieces;
  }

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
            <div className="note-title-card">
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
            </div>
            <div className="editor-meta">
              <span>
                {note
                  ? `Updated ${new Date(note.updatedAt).toLocaleString()}`
                  : "A new note"}
              </span>
              <span>{draft.content.length} characters</span>
            </div>
            <div className="note-body-card">
              <div className={`note-content-editor${showSourceHighlight && ranges.length ? " has-source-highlight" : ""}`}>
                {showSourceHighlight && ranges.length > 0 && (
                  <pre
                    ref={overlay}
                    className={`note-content-highlight-overlay${isSourceHighlightFading ? " is-fading" : ""}`}
                    aria-hidden="true"
                  >
                    {renderHighlightedContent()}
                  </pre>
                )}
                <textarea
                  ref={contentArea}
                  aria-label="Note content"
                  maxLength={5000}
                  aria-describedby={draft.content.length >= 5000 ? "content-limit" : undefined}
                  placeholder="Start writing…"
                  value={draft.content}
                  onScroll={syncOverlayScroll}
                  onChange={(event) =>
                    onDraftChange({ ...draft, content: event.target.value })
                  }
                  required
                />
              </div>
              {sourcePassages.length > 0 && ranges.length === 0 && (
                <span className="source-match-notice" role="status">
                  The indexed passage no longer matches this note.
                </span>
              )}
              {draft.content.length >= 5000 && (
                <span id="content-limit" className="limit-hint" role="status">
                  Note limit reached (5,000 characters).
                </span>
              )}
            </div>
          </form>
          {note?.summary && !hasUnsavedChanges && (
            <section className="note-summary" aria-label="AI summary">
              <h3>AI summary</h3>
              <p>{note.summary}</p>
            </section>
          )}
        </>
      ) : (
        emptyState
      )}
    </section>
  );
}