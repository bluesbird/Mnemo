import type { FormEvent } from "react";
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
  onSearchChange: (value: string) => void;
  onSelect: (note: Note) => void;
  onCreate: () => void;
  onDraftChange: (draft: NoteDraft) => void;
  onSave: (event: FormEvent<HTMLFormElement>) => void;
  onDelete: () => void;
  onSummarize: () => void;
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
  onSearchChange,
  onSelect,
  onCreate,
  onDraftChange,
  onSave,
  onDelete,
  onSummarize,
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
      />
      <NoteEditor
        note={selectedNote}
        isNew={isNew}
        draft={draft}
        saving={saving}
        summarizing={summarizing}
        hasUnsavedChanges={hasUnsavedChanges}
        error={error}
        onDraftChange={onDraftChange}
        onSave={onSave}
        onDelete={onDelete}
        onSummarize={onSummarize}
        onCreate={onCreate}
      />
    </section>
  );
}
