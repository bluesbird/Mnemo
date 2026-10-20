import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import * as notesApi from "./api/notes";

vi.mock("./api/notes", () => ({
  listNotes: vi.fn(async () => []),
  createNote: vi.fn(),
  updateNote: vi.fn(),
  deleteNote: vi.fn(),
  summarizeNote: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
beforeEach(() => {
  vi.clearAllMocks();
  window.history.replaceState(null, "", "#/notes");
  vi.mocked(notesApi.listNotes).mockResolvedValue([]);
});

it.each([false, true])("confirms and discards changes before opening chat (new note: %s)", async (isNew) => {
  const note = {
    id: 1, title: "Saved note", content: "Saved content", summary: null,
    createdAt: "2026-10-20T00:00:00", updatedAt: "2026-10-20T00:00:00",
  };
  vi.mocked(notesApi.listNotes).mockResolvedValue([note]);
  const confirm = vi.fn(() => false);
  vi.stubGlobal("confirm", confirm);
  render(<App />);
  await screen.findByText(note.title);
  fireEvent.click(isNew
    ? screen.getByRole("button", { name: "Create note" })
    : screen.getByText(note.title));
  fireEvent.change(screen.getByLabelText("Note title"), { target: { value: "Unsaved title" } });
  fireEvent.change(screen.getByLabelText("Note content"), { target: { value: "Unsaved content" } });

  fireEvent.click(screen.getByRole("button", { name: "Chat" }));
  expect(confirm).toHaveBeenCalledWith("You have unsaved changes. Discard them?");
  expect(window.location.hash).toBe("#/notes");
  expect((screen.getByLabelText("Note content") as HTMLTextAreaElement).value).toBe("Unsaved content");

  confirm.mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: "Chat" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Chat" }).className).toContain("is-active"));
  fireEvent.click(screen.getByRole("button", { name: "Notes" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Notes" }).className).toContain("is-active"));
  if (isNew) {
    expect(screen.queryByLabelText("Note content")).toBeNull();
  } else {
    expect((screen.getByLabelText("Note title") as HTMLInputElement).value).toBe(note.title);
    expect((screen.getByLabelText("Note content") as HTMLTextAreaElement).value).toBe(note.content);
  }
  expect(notesApi.createNote).not.toHaveBeenCalled();
  expect(notesApi.updateNote).not.toHaveBeenCalled();
});

it("requests a summary only on demand and clears it after saving edits", async () => {
  const note = {
    id: 1,
    title: "Manual summary example",
    content: "Original content",
    summary: null,
    createdAt: "2026-10-20T00:00:00",
    updatedAt: "2026-10-20T00:00:00",
  };
  vi.mocked(notesApi.listNotes).mockResolvedValue([note]);
  vi.mocked(notesApi.summarizeNote).mockResolvedValue({
    ...note, summary: "This note has an optional summary.",
  });
  vi.mocked(notesApi.updateNote).mockResolvedValue({ ...note, content: "Changed content" });
  render(<App />);
  fireEvent.click(await screen.findByText(note.title));
  expect(notesApi.summarizeNote).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Summarize note" }));
  await screen.findByText("This note has an optional summary.");
  expect(notesApi.summarizeNote).toHaveBeenCalledWith(1);

  const content = screen.getByLabelText("Note content");
  fireEvent.change(content, { target: { value: "Changed content" } });
  expect(screen.queryByRole("region", { name: "AI summary" })).toBeNull();
  fireEvent.submit(content.closest("form")!);
  await waitFor(() => expect(notesApi.updateNote).toHaveBeenCalledWith(1, {
    title: note.title, content: "Changed content",
  }));
  expect(notesApi.summarizeNote).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("region", { name: "AI summary" })).toBeNull();
});

describe("demo privacy information", () => {
  it("shows the shared-data warning and expandable privacy notice", async () => {
    render(<App />);

    expect(screen.getByText(/Public demo: notes are shared/)).toBeTruthy();
    const summary = screen.getByText("Privacy");
    expect(summary.closest("details")).not.toBeNull();
    expect(screen.getByText(/Lorenz Moser/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "lorenz.moser.bw@gmail.com" }).getAttribute("href"))
      .toBe("mailto:lorenz.moser.bw@gmail.com");
    expect(screen.getByText(/Hosting is provided by Contabo/)).toBeTruthy();
    expect(screen.queryByText(/TODO/)).toBeNull();
    expect(screen.getByText(/Chat history is saved in your browser/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Groq's data information" }).getAttribute("href"))
      .toBe("https://console.groq.com/docs/your-data");
    await screen.findByText("No notes yet. Create one to get started.");
  });
});
