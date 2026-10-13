import { useEffect, useMemo, useState } from "react";
import {
  createNote,
  deleteNote as deleteNoteRequest,
  enrichNote as enrichNoteRequest,
  listNotes,
  updateNote,
} from "./api/notes";
import { NoteEditor } from "./components/NoteEditor";
import { NoteList } from "./components/NoteList";
import type { Note, NoteDraft } from "./types/note";

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
      const result = await listNotes();
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
      let saved: Note;
      if (isNew) {
        saved = await createNote(draft);
      } else if (selectedNote) {
        saved = await updateNote(selectedNote.id, draft);
      } else {
        return;
      }
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
      await deleteNoteRequest(selectedNote.id);
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
      const enriched = await enrichNoteRequest(selectedNote.id);
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
        <NoteList
          notes={filteredNotes}
          totalCount={notes.length}
          selectedId={selectedId}
          loading={loading}
          search={search}
          onSearchChange={setSearch}
          onSelect={selectNote}
          onCreate={startNewNote}
        />
        <NoteEditor
          note={selectedNote}
          isNew={isNew}
          draft={draft}
          saving={saving}
          enriching={enriching}
          hasUnsavedChanges={hasUnsavedChanges}
          error={error}
          onDraftChange={setDraft}
          onSave={(event) => void saveNote(event)}
          onDelete={() => void deleteNote()}
          onEnrich={() => void enrichNote()}
          onCreate={startNewNote}
        />
      </section>
      <footer className="page-footer">
        <span>PERSONAL KNOWLEDGE HUB</span>
        <span>MS1 · NOTES</span>
      </footer>
    </main>
  );
}

export default App;
