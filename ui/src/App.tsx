import { useEffect, useMemo, useState } from "react";

type Note = {
  id: number;
  title: string;
  content: string;
  summary: string | null;
  tags: string[];
  createdAt: string;
  updatedAt: string;
};

type NoteDraft = Pick<Note, "title" | "content">;

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(
  /\/$/,
  "",
);

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/v1/notes${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed (${response.status})`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function App() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<NoteDraft>({ title: "", content: "" });
  const [isNew, setIsNew] = useState(false);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [error, setError] = useState("");

  const selectedNote = notes.find((note) => note.id === selectedId) ?? null;
  const filteredNotes = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return notes;
    return notes.filter((note) =>
      `${note.title} ${note.content} ${note.tags.join(" ")}`
        .toLowerCase()
        .includes(query),
    );
  }, [notes, search]);

  async function loadNotes() {
    setLoading(true);
    setError("");
    try {
      const result = await request<Note[]>("");
      setNotes(result);
      if (
        selectedId !== null &&
        !result.some((note) => note.id === selectedId)
      ) {
        setSelectedId(null);
        setDraft({ title: "", content: "" });
      }
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Could not load notes.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadNotes();
  }, []);

  function selectNote(note: Note) {
    setSelectedId(note.id);
    setDraft({ title: note.title, content: note.content });
    setIsNew(false);
    setError("");
  }

  function startNewNote() {
    setSelectedId(null);
    setDraft({ title: "", content: "" });
    setIsNew(true);
    setError("");
  }

  async function saveNote(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const saved = isNew
        ? await request<Note>("", {
            method: "POST",
            body: JSON.stringify(draft),
          })
        : await request<Note>(`/${selectedId}`, {
            method: "PUT",
            body: JSON.stringify(draft),
          });
      setNotes((current) =>
        isNew
          ? [saved, ...current]
          : current.map((note) => (note.id === saved.id ? saved : note)),
      );
      setSelectedId(saved.id);
      setDraft({ title: saved.title, content: saved.content });
      setIsNew(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save note.");
    } finally {
      setSaving(false);
    }
  }

  async function deleteNote() {
    if (
      !selectedNote ||
      saving ||
      enriching ||
      !window.confirm(`Delete “${selectedNote.title}”?`)
    )
      return;
    setError("");
    try {
      await request<void>(`/${selectedNote.id}`, { method: "DELETE" });
      setNotes((current) =>
        current.filter((note) => note.id !== selectedNote.id),
      );
      setSelectedId(null);
      setDraft({ title: "", content: "" });
      setIsNew(false);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Could not delete note.",
      );
    }
  }

  async function enrichNote() {
    if (!selectedNote || saving || enriching) return;
    setEnriching(true);
    setError("");
    try {
      const enriched = await request<Note>(`/${selectedNote.id}/ai-enrich`, {
        method: "POST",
      });
      setNotes((current) =>
        current.map((note) => (note.id === enriched.id ? enriched : note)),
      );
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Could not enrich note.",
      );
    } finally {
      setEnriching(false);
    }
  }

  const hasEditor = isNew || selectedNote !== null;
  const canSave =
    draft.title.trim().length > 0 && draft.content.trim().length > 0;
  const hasUnsavedChanges =
    selectedNote !== null &&
    (draft.title !== selectedNote.title ||
      draft.content !== selectedNote.content);

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#" aria-label="Personal Knowledge Hub home">
          <span className="brand-mark">p</span>
          <span>Personal Knowledge Hub</span>
        </a>
        <span className="topbar-label">YOUR LIBRARY</span>
      </header>

      <section className="workspace" aria-label="Notes">
        <aside className="note-sidebar">
          <div className="sidebar-heading">
            <div>
              <p className="eyebrow">COLLECTION</p>
              <h1>
                Notes <span>{notes.length}</span>
              </h1>
            </div>
            <button
              className="new-button"
              type="button"
              onClick={startNewNote}
              aria-label="Create note"
            >
              <span aria-hidden="true">+</span> New note
            </button>
          </div>

          <label className="search-box">
            <span aria-hidden="true" className="search-icon">
              ⌕
            </span>
            <input
              type="search"
              placeholder="Search notes"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <kbd>/</kbd>
          </label>

          <div className="note-list" aria-label="Note list">
            {loading && <p className="list-message">Loading notes…</p>}
            {!loading && filteredNotes.length === 0 && (
              <p className="list-message">
                {search
                  ? "No matching notes."
                  : "No notes yet. Create one to get started."}
              </p>
            )}
            {filteredNotes.map((note) => (
              <button
                className={`note-row${selectedId === note.id ? " is-selected" : ""}`}
                key={note.id}
                type="button"
                onClick={() => selectNote(note)}
              >
                <span className="note-row-title">{note.title}</span>
                <span className="note-row-preview">{note.content}</span>
                <span className="note-row-date">
                  {new Date(note.updatedAt).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              </button>
            ))}
          </div>
          <div className="sidebar-footer">
            {notes.length} {notes.length === 1 ? "note" : "notes"} in your
            library
          </div>
        </aside>

        <section className="editor-panel" aria-label="Note editor">
          {error && (
            <div className="error-banner" role="alert">
              {error}
            </div>
          )}
          {hasEditor ? (
            <>
              <div className="editor-toolbar">
                <span>
                  {isNew ? "NEW NOTE" : `NOTE  /  ${selectedNote?.id}`}
                </span>
                <div className="toolbar-actions">
                  {selectedNote && (
                    <>
                      <button
                        className="text-button enrich-button"
                        type="button"
                        onClick={() => void enrichNote()}
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
                        onClick={() => void deleteNote()}
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
              <form
                id="note-form"
                className="note-form"
                onSubmit={(event) => void saveNote(event)}
              >
                <input
                  className="title-input"
                  aria-label="Note title"
                  placeholder="Untitled note"
                  value={draft.title}
                  onChange={(event) =>
                    setDraft({ ...draft, title: event.target.value })
                  }
                  required
                />
                <div className="editor-meta">
                  <span>
                    {selectedNote
                      ? `Updated ${new Date(selectedNote.updatedAt).toLocaleString()}`
                      : "A new note"}
                  </span>
                  <span>{draft.content.length} characters</span>
                </div>
                <textarea
                  aria-label="Note content"
                  placeholder="Start writing…"
                  value={draft.content}
                  onChange={(event) =>
                    setDraft({ ...draft, content: event.target.value })
                  }
                  required
                />
              </form>
              {selectedNote &&
                (selectedNote.summary || selectedNote.tags.length > 0) && (
                  <div className="note-extras">
                    {selectedNote.summary && <p>{selectedNote.summary}</p>}
                    {selectedNote.tags.length > 0 && (
                      <div className="tags">
                        {selectedNote.tags.map((tag) => (
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
              <button
                className="new-button"
                type="button"
                onClick={startNewNote}
              >
                ＋ New note
              </button>
            </div>
          )}
        </section>
      </section>
      <footer className="page-footer">
        <span>PERSONAL KNOWLEDGE HUB</span>
        <span>MS1 · NOTES</span>
      </footer>
    </main>
  );
}

export default App;
