import type { FormEvent, ReactNode } from "react";
import type { Note, NoteDraft } from "../types/note";
import { NoteEditor } from "./NoteEditor";
import { NoteList } from "./NoteList";

type NotesWorkspaceProps = {
  notes: Note[];
  filteredNotes: Note[];
  selectedId: number | null;
  selectedNote: Note | null;
  draft: NoteDraft;
  isNew: boolean;
  search: string;
  loading: boolean;
  saving: boolean;
  summarizing: boolean;
  error: string;
  hasUnsavedChanges: boolean;
  sourcePassages?: string[];
  onSearchChange: (value: string) => void;
  onSelect: (note: Note) => void;
  onCreate: () => void;
  onAskChat: () => void;
  onDraftChange: (draft: NoteDraft) => void;
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: () => void;
  onSummarize: () => void;
  chatWorkspace: ReactNode;
};

export function NotesWorkspace({
  notes,
  filteredNotes,
  selectedId,
  selectedNote,
  draft,
  isNew,
  search,
  loading,
  saving,
  summarizing,
  error,
  hasUnsavedChanges,
  sourcePassages = [],
  onSearchChange,
  onSelect,
  onCreate,
  onAskChat,
  onDraftChange,
  onSave,
  onDelete,
  onSummarize,
  chatWorkspace,
}: NotesWorkspaceProps) {
  return (
    <section className="workspace" aria-label="Notes">
      <NoteList
        notes={filteredNotes}
        totalCount={notes.length}
        selectedId={selectedId}
        loading={loading}
        search={search}
        onSearchChange={onSearchChange}
        onSelect={onSelect}
        onCreate={onCreate}
        onAskChat={onAskChat}
      />
      <NoteEditor
        note={selectedNote}
        isNew={isNew}
        draft={draft}
        saving={saving}
        summarizing={summarizing}
        hasUnsavedChanges={hasUnsavedChanges}
        sourcePassages={sourcePassages}
        error={error}
        onDraftChange={onDraftChange}
        onSave={onSave}
        onDelete={onDelete}
        onSummarize={onSummarize}
        emptyState={chatWorkspace}
      />
    </section>
  );
}
