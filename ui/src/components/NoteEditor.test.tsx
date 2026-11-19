import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NoteEditor } from "./NoteEditor";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

it("shows limit hints only at the title and content boundaries", () => {
  const props = {
    note: null,
    isNew: true,
    draft: { title: "t".repeat(69), content: "c".repeat(4999) },
    saving: false,
    summarizing: false,
    hasUnsavedChanges: true,
    error: "",
    onDraftChange: vi.fn(),
    onSave: vi.fn(),
    onDelete: vi.fn(),
    onSummarize: vi.fn(),
  };
  const { rerender } = render(<NoteEditor {...props} />);
  expect(screen.getByLabelText("Note title").getAttribute("maxlength")).toBe("70");
  expect(screen.queryByText(/limit reached/)).toBeNull();

  rerender(<NoteEditor {...props} draft={{ title: "t".repeat(70), content: "c".repeat(5000) }} />);
  expect(screen.getByText("Title limit reached (70 characters).")).toBeTruthy();
  expect(screen.getByText("Note limit reached (5,000 characters).")).toBeTruthy();

  rerender(<NoteEditor {...props} />);
  expect(screen.queryByText(/limit reached/)).toBeNull();
});

it("highlights matching retrieved chunks without changing the note", () => {
  const note = {
    id: 1,
    title: "Bluebird",
    content: "Intro text.\n\nThe first line is here.\n\nThe second line is here.",
    summary: null,
    createdAt: "2026-10-20T00:00:00",
    updatedAt: "2026-10-20T00:00:00",
  };
  const props = {
    note,
    isNew: false,
    draft: { title: note.title, content: note.content },
    saving: false,
    summarizing: false,
    hasUnsavedChanges: false,
    error: "",
    onDraftChange: vi.fn(),
    onSave: vi.fn(),
    onDelete: vi.fn(),
    onSummarize: vi.fn(),
    sourcePassages: [
      "Bluebird\n\nThe first line is \n here.",
      "The second line is here.",
    ],
  };
  render(<NoteEditor {...props} />);

  expect(Array.from(document.querySelectorAll("mark")).map((mark) => mark.textContent)).toEqual([
    "The first line is here.",
    "The second line is here.",
  ]);
  expect((screen.getByLabelText("Note content") as HTMLTextAreaElement).value)
    .toBe(note.content);
  const contentArea = screen.getByLabelText("Note content") as HTMLTextAreaElement;
  expect(document.activeElement).toBe(contentArea);
  expect(contentArea.selectionStart).toBe(note.content.indexOf("The first line"));
  expect(document.querySelector(".note-content-highlight-overlay")?.getAttribute("aria-hidden"))
    .toBe("true");
});

it("scrolls the first highlighted passage to the top of the editor", () => {
  vi.useFakeTimers();
  const content = "Intro text.\n\nThe matching passage.";
  render(
    <NoteEditor
      note={{
        id: 5,
        title: "Scroll test",
        content,
        summary: null,
        createdAt: "2026-10-20T00:00:00",
        updatedAt: "2026-10-20T00:00:00",
      }}
      isNew={false}
      draft={{ title: "Scroll test", content }}
      saving={false}
      summarizing={false}
      hasUnsavedChanges={false}
      error=""
      onDraftChange={vi.fn()}
      onSave={vi.fn()}
      onDelete={vi.fn()}
      onSummarize={vi.fn()}
      sourcePassages={["The matching passage."]}
    />,
  );

  const area = screen.getByLabelText("Note content") as HTMLTextAreaElement;
  const highlight = document.querySelector("mark")!;
  const highlightOverlay = document.querySelector("pre")!;
  vi.spyOn(highlight, "getBoundingClientRect").mockReturnValue(
    new DOMRect(0, 250, 100, 20),
  );
  vi.spyOn(highlightOverlay, "getBoundingClientRect").mockReturnValue(
    new DOMRect(0, 100, 300, 300),
  );

  act(() => vi.advanceTimersByTime(16));

  expect(area.scrollTop).toBe(146);
  expect(highlightOverlay.scrollTop).toBe(area.scrollTop);
});

it("does not highlight a retrieved passage that no longer matches", () => {
  const note = {
    id: 2,
    title: "Edited note",
    content: "Changed content",
    summary: null,
    createdAt: "2026-10-20T00:00:00",
    updatedAt: "2026-10-20T00:00:00",
  };
  render(
    <NoteEditor
      note={note}
      isNew={false}
      draft={{ title: note.title, content: note.content }}
      saving={false}
      summarizing={false}
      hasUnsavedChanges={false}
      error=""
      onDraftChange={vi.fn()}
      onSave={vi.fn()}
      onDelete={vi.fn()}
      onSummarize={vi.fn()}
      sourcePassages={["Old indexed content"]}
    />,
  );

  expect(screen.getByRole("status").textContent)
    .toBe("The indexed passage no longer matches this note.");
  expect(document.querySelector("mark")).toBeNull();
});

it("merges overlapping retrieved chunks before rendering highlights", () => {
  const content = "The bird sat on the telephone line.";
  render(
    <NoteEditor
      note={{
        id: 3,
        title: "Bird",
        content,
        summary: null,
        createdAt: "2026-10-20T00:00:00",
        updatedAt: "2026-10-20T00:00:00",
      }}
      isNew={false}
      draft={{ title: "Bird", content }}
      saving={false}
      summarizing={false}
      hasUnsavedChanges={false}
      error=""
      onDraftChange={vi.fn()}
      onSave={vi.fn()}
      onDelete={vi.fn()}
      onSummarize={vi.fn()}
      sourcePassages={[
        "The bird sat on the",
        "sat on the telephone line.",
      ]}
    />,
  );

  expect(Array.from(document.querySelectorAll("mark")).map((mark) => mark.textContent))
    .toEqual([content]);
  expect(document.querySelector(".note-content-highlight-overlay")?.textContent)
    .toBe(content);
});

it("fades the source highlight after three seconds", () => {
  vi.useFakeTimers();
  const note = {
    id: 4,
    title: "Fade test",
    content: "Passage to highlight.",
    summary: null,
    createdAt: "2026-10-20T00:00:00",
    updatedAt: "2026-10-20T00:00:00",
  };
  render(
    <NoteEditor
      note={note}
      isNew={false}
      draft={{ title: note.title, content: note.content }}
      saving={false}
      summarizing={false}
      hasUnsavedChanges={false}
      error=""
      onDraftChange={vi.fn()}
      onSave={vi.fn()}
      onDelete={vi.fn()}
      onSummarize={vi.fn()}
      sourcePassages={[note.content]}
    />,
  );

  expect(document.querySelector(".note-content-highlight-overlay.is-fading")).toBeNull();
  act(() => vi.advanceTimersByTime(3000));
  expect(document.querySelector(".note-content-highlight-overlay.is-fading")).not.toBeNull();
  act(() => vi.advanceTimersByTime(500));
  expect(document.querySelector(".note-content-highlight-overlay")).toBeNull();
});
