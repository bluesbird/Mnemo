import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NoteEditor } from "./NoteEditor";

afterEach(cleanup);

it("shows limit hints only at the title and content boundaries", () => {
  const props = {
    note: null,
    isNew: true,
    draft: { title: "t".repeat(69), content: "c".repeat(4999) },
    saving: false,
    enriching: false,
    hasUnsavedChanges: true,
    error: "",
    onDraftChange: vi.fn(),
    onSave: vi.fn(),
    onDelete: vi.fn(),
    onEnrich: vi.fn(),
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
