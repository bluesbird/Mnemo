import type { Note } from "../types/note";
import { SearchBar } from "./SearchBar";

type NoteListProps = {
  notes: Note[];
  totalCount: number;
  selectedId: number | null;
  loading: boolean;
  search: string;
  onSearchChange: (value: string) => void;
  onSelect: (note: Note) => void;
  onCreate: () => void;
};

export function NoteList({
  notes,
  totalCount,
  selectedId,
  loading,
  search,
  onSearchChange,
  onSelect,
  onCreate,
}: NoteListProps) {
  return (
    <aside className="note-sidebar">
      <div className="sidebar-heading">
        <div>
          <p className="eyebrow">COLLECTION</p>
          <h1>
            Notes <span>{totalCount}</span>
          </h1>
        </div>
        <button
          className="new-button"
          type="button"
          onClick={onCreate}
          aria-label="Create note"
          disabled={totalCount >= 100}
          title={totalCount >= 100 ? "Delete a note before adding another (100-note limit)." : undefined}
        >
          <span aria-hidden="true">+</span> New note
        </button>
      </div>

      <SearchBar value={search} onChange={onSearchChange} />

      <div className="note-list" aria-label="Note list">
        {loading && <p className="list-message">Loading notes…</p>}
        {!loading && notes.length === 0 && (
          <p className="list-message">
            {search
              ? "No matching notes."
              : "No notes yet. Create one to get started."}
          </p>
        )}
        {notes.map((note) => (
          <button
            className={`note-row${selectedId === note.id ? " is-selected" : ""}`}
            key={note.id}
            type="button"
            onClick={() => onSelect(note)}
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
        {totalCount >= 100
          ? "100-note limit reached. Delete a note to add another."
          : `${totalCount} ${totalCount === 1 ? "note" : "notes"} in your library`}
      </div>
    </aside>
  );
}