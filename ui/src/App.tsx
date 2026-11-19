import { useEffect, useMemo, useState } from "react";
import {
  createNote,
  deleteNote as deleteNoteRequest,
  summarizeNote as summarizeNoteRequest,
  listNotes,
  updateNote,
} from "./api/notes";
import { ChatWorkspace } from "./components/ChatWorkspace";
import { NotesWorkspace } from "./components/NotesWorkspace";
import type { ChatMessage } from "./types/chat";
import type { Note, NoteDraft } from "./types/note";

const CHAT_STORAGE_KEY = "pkh.chat";
const THEME_STORAGE_KEY = "mnemo.theme.v1";

type ThemeOverride = "light" | "dark" | null;

function sortNotesNewestFirst(notes: Note[]): Note[] {
  return [...notes].sort(
    (a, b) =>
      b.updatedAt.localeCompare(a.updatedAt) ||
      b.id - a.id,
  );
}

function loadThemeOverride(): ThemeOverride {
  try {
    const savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    return savedTheme === "light" || savedTheme === "dark" ? savedTheme : null;
  } catch {
    return null;
  }
}

function loadChatMessages(): ChatMessage[] {
  try {
    const parsed = JSON.parse(sessionStorage.getItem(CHAT_STORAGE_KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function AboutPage() {
  return (
    <div className="about-view">
      <article className="about-page">
        <h1>About Mnemo</h1>
        <p className="about-lead">
          Mnemo is a personal knowledge hub for storing notes, generating AI
          summaries, and finding grounded answers from your own content.
        </p>

        <section aria-labelledby="about-privacy-title">
          <h2 id="about-privacy-title">Privacy</h2>
          <p>
            This is a public, shared demo. Anyone can read, edit or delete its
            notes. Do not enter personal, confidential or sensitive information.
            Notes, summaries and search-index entries remain on the server until
            deleted or reset.
          </p>
          <p>
            The server processes IP addresses, request paths and timestamps to
            deliver the app, apply rate limits and diagnose problems.
          </p>
          <p>
            Chat history stays in your browser&apos;s session storage and is sent
            with chat requests. Relevant note excerpts and content you summarize
            are sent to GroqCloud. Search embeddings run locally on the server
            using Ollama and Chroma. The app uses no analytics or advertising
            trackers.
          </p>
          <p>
            Groq may temporarily log inference data and retains usage metadata.
            Zero Data Retention is disabled for this deployment. See{" "}
            <a href="https://console.groq.com/docs/your-data">
              Groq&apos;s data information
            </a>.
          </p>
          <p>
            For privacy requests or your applicable data-protection rights,
            contact the operator below.
          </p>
        </section>

        <section aria-labelledby="about-imprint-title">
          <h2 id="about-imprint-title">Imprint</h2>
          <p>
            <strong>Operator and privacy contact:</strong> Lorenz Moser
            <br />
            <a href="mailto:lorenz.moser.bw@gmail.com">
              lorenz.moser.bw@gmail.com
            </a>
          </p>
          <p>Hosting is provided by Contabo.</p>
        </section>
      </article>
    </div>
  );
}

function App() {
  const isAboutPage = window.location.pathname === "/about";
  const [notes, setNotes] = useState<Note[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<NoteDraft>({ title: "", content: "" });
  const [isNew, setIsNew] = useState(false);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [error, setError] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(loadChatMessages);
  const [themeOverride, setThemeOverride] = useState<ThemeOverride>(loadThemeOverride);
  const [systemDarkMode, setSystemDarkMode] = useState(() =>
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-color-scheme: dark)").matches
  );
  const [themeError, setThemeError] = useState("");
  const [sourceHighlight, setSourceHighlight] = useState<{
    noteId: number;
    passages: string[];
  } | null>(null);

  const [suggestionSeed, setSuggestionSeed] = useState(0);
  const darkMode = themeOverride === null ? systemDarkMode : themeOverride === "dark";
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
      `${note.title} ${note.content}`
        .toLowerCase()
        .includes(query),
    );
  }, [notes, search]);

  async function loadNotes() {
    setLoading(true);
    setError("");
    try {
      const result = await listNotes();
      setNotes(sortNotesNewestFirst(result));
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
    if (!isAboutPage) void loadNotes();
  }, [isAboutPage]);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const preference = window.matchMedia("(prefers-color-scheme: dark)");
    const updateSystemTheme = () => setSystemDarkMode(preference.matches);
    preference.addEventListener("change", updateSystemTheme);
    return () => preference.removeEventListener("change", updateSystemTheme);
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? "dark" : "light";
  }, [darkMode]);

  useEffect(() => {
    if (window.location.hash) {
      window.history.replaceState(
        null,
        "",
        `${window.location.pathname}${window.location.search}`,
      );
    }
  }, []);

  function selectNote(note: Note) {
    setSelectedId(note.id);
    setDraft({ title: note.title, content: note.content });
    setIsNew(false);
    setSourceHighlight(null);
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
    if (notes.length >= 100) {
      setError("The 100-note limit has been reached. Delete a note before adding another.");
      return;
    }
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
        sortNotesNewestFirst(isNew
          ? [saved, ...current]
          : current.map((note) => (note.id === saved.id ? saved : note))),
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
      summarizing ||
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

  async function summarizeNote() {
    if (!selectedNote || saving || summarizing || hasUnsavedChanges) return;
    setSummarizing(true);
    setError("");
    try {
      const summarized = await summarizeNoteRequest(selectedNote.id);
      setNotes((current) =>
        sortNotesNewestFirst(
          current.map((note) => (note.id === summarized.id ? summarized : note)),
        ),
      );
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Could not summarize note.",
      );
    } finally {
      setSummarizing(false);
    }
  }

  const hasUnsavedChanges =
    selectedNote !== null &&
    (draft.title !== selectedNote.title ||
      draft.content !== selectedNote.content);

  function openEmbeddedChat() {
    if (!confirmDiscardChanges()) return;
    setSelectedId(null);
    setDraft({ title: "", content: "" });
    setIsNew(false);
    setSourceHighlight(null);
    setError("");
  }

  function toggleTheme() {
    const nextTheme = darkMode ? "light" : "dark";
    setThemeOverride(nextTheme);
    setThemeError("");
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    } catch {
      setThemeError("Your theme preference could not be saved in browser storage.");
    }
  }

  async function openNoteFromChat(noteId: number, passages: string[]) {
    if (selectedId !== noteId && !confirmDiscardChanges()) return;

    const current = notes.find((note) => note.id === noteId);
    if (current) {
      if (selectedId !== noteId) selectNote(current);
      setSourceHighlight({ noteId, passages });
      return;
    }

    setError("");
    try {
      const result = await listNotes();
      setNotes(sortNotesNewestFirst(result));
      const match = result.find((note) => note.id === noteId);
      if (match) {
        selectNote(match);
        setSourceHighlight({ noteId, passages });
      } else {
        setError(`Source note #${noteId} is no longer available.`);
      }
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not load the source note.",
      );
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <a
          className="brand"
          href="/"
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
            <span className="brand-subtitle">Personal Knowledge Hub</span>
          </span>
        </a>
        <nav className="topbar-nav" aria-label="Primary navigation">
          <button
            type="button"
            className="topbar-theme-button"
            onClick={toggleTheme}
            aria-label={darkMode ? "Switch to light mode" : "Switch to dark mode"}
            aria-pressed={darkMode}
          >
            {darkMode ? (
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M20.5 15.1A8.8 8.8 0 0 1 8.9 3.5a8.8 8.8 0 1 0 11.6 11.6Z" />
              </svg>
            )}
          </button>
          <a
            className="topbar-repo-link"
            href="https://github.com/bluesbird/Mnemo"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Mnemo on GitHub (opens in a new tab)"
            title="View Mnemo on GitHub"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M12 .75a11.25 11.25 0 0 0-3.56 21.92c.56.1.77-.24.77-.54v-2.1c-3.13.68-3.79-1.33-3.79-1.33-.51-1.3-1.25-1.65-1.25-1.65-1.02-.7.08-.68.08-.68 1.13.08 1.73 1.16 1.73 1.16 1 1.72 2.63 1.22 3.27.93.1-.73.39-1.22.71-1.5-2.5-.28-5.13-1.25-5.13-5.56 0-1.23.44-2.23 1.16-3.02-.12-.28-.5-1.43.11-2.98 0 0 .95-.3 3.1 1.15a10.8 10.8 0 0 1 5.64 0c2.15-1.46 3.1-1.15 3.1-1.15.61 1.55.23 2.7.11 2.98.72.79 1.16 1.79 1.16 3.02 0 4.32-2.64 5.28-5.15 5.56.4.35.76 1.03.76 2.08v3.09c0 .3.2.65.78.54A11.25 11.25 0 0 0 12 .75Z" />
            </svg>
          </a>
        </nav>
      </header>

      {themeError && (
        <p className="theme-storage-error" role="status">
          {themeError}
        </p>
      )}

      {isAboutPage ? (
        <AboutPage />
      ) : (
        <div className="view">
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
            summarizing={summarizing}
            error={error}
            hasUnsavedChanges={hasUnsavedChanges}
            onSearchChange={setSearch}
            onSelect={selectNoteGuarded}
            onCreate={startNewNoteGuarded}
            onAskChat={openEmbeddedChat}
            onDraftChange={setDraft}
            onSave={(event) => void saveNote(event)}
            onDelete={() => void deleteNote()}
            onSummarize={() => void summarizeNote()}
            sourcePassages={
              sourceHighlight?.noteId === selectedId
                ? sourceHighlight.passages
                : []
            }
            chatWorkspace={
              <ChatWorkspace
                embedded
                messages={chatMessages}
                onMessagesChange={setChatMessages}
                suggestions={chatSuggestions}
                onClear={() => setSuggestionSeed((seed) => seed + 1)}
                onOpenNote={(noteId, passages) =>
                  void openNoteFromChat(noteId, passages)
                }
              />
            }
          />
        </div>
      )}

      <footer className="page-footer">
        <p className="demo-notice">
          <strong>Public demo:</strong> notes are shared and anyone can change or delete them.
          Use fictional data only. AI requests send note content to Groq; answers may be wrong.
        </p>
        <a className="about-link" href="/about">
          About Mnemo
        </a>
      </footer>
    </main>
  );
}

export default App;
