import { useEffect, useMemo, useState } from "react";
import {
  createNote,
  deleteNote as deleteNoteRequest,
  enrichNote as enrichNoteRequest,
  listNotes,
  updateNote,
} from "./api/notes";
import { ChatWorkspace } from "./components/ChatWorkspace";
import { NotesWorkspace } from "./components/NotesWorkspace";
import type { ChatMessage } from "./types/chat";
import type { Note, NoteDraft } from "./types/note";

type AppView = "notes" | "chat";

const CHAT_STORAGE_KEY = "pkh.chat";

function loadChatMessages(): ChatMessage[] {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(CHAT_STORAGE_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function parseViewFromHash(): AppView {
  return window.location.hash === "#/chat" ? "chat" : "notes";
}

function App() {
  const [view, setView] = useState<AppView>(() => parseViewFromHash());
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<NoteDraft>({ title: "", content: "" });
  const [isNew, setIsNew] = useState(false);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [error, setError] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(loadChatMessages);

  const [suggestionSeed, setSuggestionSeed] = useState(0);
  const chatIsEmpty = chatMessages.length === 0;
  const chatSuggestions = useMemo(() => {
    const byRecent = [...notes].sort((a, b) =>
      b.updatedAt.localeCompare(a.updatedAt),
    );
    const picked = byRecent.slice(0, 2);
    const rest = byRecent.slice(2);
    if (rest.length > 0) {
      picked.push(rest[Math.floor(Math.random() * rest.length)]);
    }
    return picked.map((note) => `What do my notes say about ${note.title}?`);
    // chatIsEmpty and suggestionSeed re-roll the random pick on clear
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notes, chatIsEmpty, suggestionSeed]);

  useEffect(() => {
    try {
      sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(chatMessages));
    } catch {
      // storage unavailable: chat simply stays in memory
    }
  }, [chatMessages]);

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

  useEffect(() => {
    function onHashChange() {
      setView(parseViewFromHash());
    }

    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    if (!window.location.hash) {
      window.location.hash = "#/notes";
    }
  }, []);

  function selectNote(note: Note) {
    setSelectedId(note.id);
    setDraft({ title: note.title, content: note.content });
    setIsNew(false);
    setError("");
  }

  function confirmDiscardChanges(): boolean {
    const hasUnsavedNewNote =
      isNew && (draft.title.trim() !== "" || draft.content.trim() !== "");
    return (
      !(hasUnsavedChanges || hasUnsavedNewNote) ||
      window.confirm("You have unsaved changes. Discard them?")
    );
  }

  function selectNoteGuarded(note: Note) {
    if (note.id === selectedId || !confirmDiscardChanges()) return;
    selectNote(note);
  }

  function startNewNoteGuarded() {
    if (!confirmDiscardChanges()) return;
    startNewNote();
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

  function goToNotes() {
    window.location.hash = "#/notes";
  }

  function goToChat() {
    window.location.hash = "#/chat";
  }

  async function openNoteFromChat(noteId: number) {
    if (selectedId !== noteId && !confirmDiscardChanges()) return;

    const current = notes.find((note) => note.id === noteId);
    if (current) {
      selectNote(current);
      goToNotes();
      return;
    }

    setError("");
    try {
      const result = await listNotes();
      setNotes(result);
      const match = result.find((note) => note.id === noteId);
      if (match) {
        selectNote(match);
      } else {
        setError(`Source note #${noteId} is no longer available.`);
      }
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not load the source note.",
      );
    } finally {
      goToNotes();
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a
          className="brand"
          href="#/notes"
          aria-label="Mnemo notes"
        >
          <img
            className="brand-mark"
            src="/mnemo.svg"
            alt=""
            width="38"
            height="38"
          />
          <span className="brand-copy">
            <span className="brand-name">Mnemo</span>
            <span className="brand-subtitle">Your personal knowledge hub</span>
          </span>
        </a>
        <nav className="topbar-nav" aria-label="Primary navigation">
          <button
            type="button"
            className={`topbar-nav-button${view === "notes" ? " is-active" : ""}`}
            onClick={goToNotes}
          >
            Notes
          </button>
          <button
            type="button"
            className={`topbar-nav-button${view === "chat" ? " is-active" : ""}`}
            onClick={goToChat}
          >
            Chat
          </button>
        </nav>
      </header>

      <div className={view === "notes" ? "view" : "view is-hidden"}>
        <NotesWorkspace
          notes={notes}
          filteredNotes={filteredNotes}
          selectedId={selectedId}
          selectedNote={selectedNote}
          draft={draft}
          isNew={isNew}
          search={search}
          loading={loading}
          saving={saving}
          enriching={enriching}
          error={error}
          hasUnsavedChanges={hasUnsavedChanges}
          onSearchChange={setSearch}
          onSelect={selectNoteGuarded}
          onCreate={startNewNoteGuarded}
          onDraftChange={setDraft}
          onSave={(event) => void saveNote(event)}
          onDelete={() => void deleteNote()}
          onEnrich={() => void enrichNote()}
        />
      </div>
      <div className={view === "chat" ? "view" : "view is-hidden"}>
        <ChatWorkspace
          messages={chatMessages}
          onMessagesChange={setChatMessages}
          suggestions={chatSuggestions}
          onClear={() => setSuggestionSeed((seed) => seed + 1)}
          onOpenNote={(noteId) => void openNoteFromChat(noteId)}
        />
      </div>

      <footer className="page-footer">
        <span>MNEMO</span>
        <span>{view === "notes" ? "NOTES" : "CHAT"}</span>
      </footer>
    </main>
  );
}

export default App;
