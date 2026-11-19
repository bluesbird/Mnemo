import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
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
  sessionStorage.clear();
  localStorage.removeItem("mnemo.theme.v1");
  document.documentElement.dataset.theme = "light";
  window.history.replaceState(null, "", "/");
  vi.mocked(notesApi.listNotes).mockResolvedValue([]);
});

it("toggles and persists the theme preference", async () => {
  render(<App />);

  fireEvent.click(screen.getByRole("button", { name: "Switch to dark mode" }));
  await waitFor(() => expect(document.documentElement.dataset.theme).toBe("dark"));
  expect(localStorage.getItem("mnemo.theme.v1")).toBe("dark");

  fireEvent.click(screen.getByRole("button", { name: "Switch to light mode" }));
  await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
  expect(localStorage.getItem("mnemo.theme.v1")).toBe("light");
});

it("restores a saved dark theme", async () => {
  localStorage.setItem("mnemo.theme.v1", "dark");
  render(<App />);

  await waitFor(() => expect(document.documentElement.dataset.theme).toBe("dark"));
  expect(screen.getByRole("button", { name: "Switch to light mode" })).toBeTruthy();
});

it("orders notes by updated date and id, newest first", async () => {
  vi.mocked(notesApi.listNotes).mockResolvedValue([
    {
      id: 2, title: "Same date, lower id", content: "Content", summary: null,
      createdAt: "2026-10-20T00:00:00", updatedAt: "2026-10-21T00:00:00",
    },
    {
      id: 1, title: "Oldest", content: "Content", summary: null,
      createdAt: "2026-10-20T00:00:00", updatedAt: "2026-10-20T00:00:00",
    },
    {
      id: 3, title: "Same date, higher id", content: "Content", summary: null,
      createdAt: "2026-10-20T00:00:00", updatedAt: "2026-10-21T00:00:00",
    },
  ]);

  render(<App />);

  await screen.findByText("Same date, higher id");
  const rows = Array.from(document.querySelectorAll(".note-row"));
  expect(rows.map((row) => row.textContent)).toEqual([
    expect.stringContaining("Same date, higher id"),
    expect.stringContaining("Same date, lower id"),
    expect.stringContaining("Oldest"),
  ]);
});

it("explains the collection limit and disables creation at 100 notes", async () => {
  vi.mocked(notesApi.listNotes).mockResolvedValue(Array.from({ length: 100 }, (_, id) => ({
    id, title: `Note ${id}`, content: "Content", summary: null,
    createdAt: "2026-10-20T00:00:00", updatedAt: "2026-10-20T00:00:00",
  })));
  render(<App />);
  await screen.findByText("100-note limit reached. Delete a note to add another.");
  expect((screen.getByRole("button", { name: "Create note" }) as HTMLButtonElement).disabled).toBe(true);
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

  fireEvent.click(screen.getByRole("button", { name: "Ask Chatbot" }));
  expect(confirm).toHaveBeenCalledWith("You have unsaved changes. Discard them?");
  expect(window.location.pathname).toBe("/");
  expect(window.location.hash).toBe("");
  expect((screen.getByLabelText("Note content") as HTMLTextAreaElement).value).toBe("Unsaved content");

  confirm.mockReturnValue(true);
  fireEvent.click(screen.getByRole("button", { name: "Ask Chatbot" }));
  await screen.findByRole("heading", { name: "Ask anything about your notes." });
  expect(window.location.pathname).toBe("/");
  expect(window.location.hash).toBe("");
  if (isNew) {
    expect(screen.queryByLabelText("Note content")).toBeNull();
  } else {
    fireEvent.click(screen.getByText(note.title));
    await screen.findByLabelText("Note content");
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
  await waitFor(() => expect((screen.getByRole("button", { name: "Summarize note" }) as HTMLButtonElement).disabled).toBe(false));
  expect(notesApi.summarizeNote).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("region", { name: "AI summary" })).toBeNull();
});

it("shows the shared-data warning and expandable privacy notice", async () => {
  render(<App />);

  expect(screen.getByText(/Public demo: notes are shared/)).toBeTruthy();
  const summary = screen.getByText("Privacy");
  expect(summary.closest("details")).not.toBeNull();
  expect(screen.getByText(/Chat history is saved in your browser/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "Groq's data information" }).getAttribute("href"))
    .toBe("https://console.groq.com/docs/your-data");
  await screen.findByText("No notes yet. Create one to get started.");
});

it("opens the cited note and highlights its retrieved chunk", async () => {
  const note = {
    id: 1,
    title: "Bluebird",
    content: "The bluebird sings on a telephone line.",
    summary: null,
    createdAt: "2026-10-20T00:00:00",
    updatedAt: "2026-10-20T00:00:00",
  };
  vi.mocked(notesApi.listNotes).mockResolvedValue([note]);
  sessionStorage.setItem("pkh.chat", JSON.stringify([{
    id: "answer",
    role: "assistant",
    text: "It is on a telephone line.",
    sources: [{
      note_id: note.id,
      note_title: note.title,
      chunk_index: 0,
      source_hash: "hash",
      score: 0.9,
      excerpt: note.content,
      chunk_text: `${note.title}\n\n${note.content}`,
    }],
  }]));
  render(<App />);

  fireEvent.click(await screen.findByRole("button", { name: note.title }));

  await screen.findByLabelText("Note content");
  expect(document.querySelector("mark")?.textContent).toBe(note.content);
  expect((screen.getByLabelText("Note content") as HTMLTextAreaElement).value)
    .toBe(note.content);
});
