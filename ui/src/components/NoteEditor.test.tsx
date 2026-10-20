import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NoteEditor } from "./NoteEditor";

afterEach(cleanup);

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
    onCreate: vi.fn(),
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

it("summarizes only on click and hides stale summaries while editing", () => {
  const note = {
    id: 1,
    title: "Title",
    content: "Content",
    summary: "This note has a summary.",
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
    onCreate: vi.fn(),
  };
  const { rerender } = render(<NoteEditor {...props} />);
  expect(props.onSummarize).not.toHaveBeenCalled();
  expect(screen.getByRole("region", { name: "AI summary" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Summarize note" }));
  expect(props.onSummarize).toHaveBeenCalledTimes(1);

  rerender(<NoteEditor {...props} hasUnsavedChanges />);
  expect(screen.queryByRole("region", { name: "AI summary" })).toBeNull();
  expect((screen.getByRole("button", { name: "Summarize note" }) as HTMLButtonElement).disabled).toBe(true);

  rerender(<NoteEditor {...props} summarizing />);
  expect((screen.getByRole("button", { name: "Summarizing…" }) as HTMLButtonElement).disabled).toBe(true);

  rerender(<NoteEditor {...props} note={null} isNew />);
  expect(screen.queryByRole("button", { name: "Summarize note" })).toBeNull();
});
