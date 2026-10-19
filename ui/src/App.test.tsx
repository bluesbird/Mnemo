import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./api/notes", () => ({
  listNotes: vi.fn(async () => []),
  createNote: vi.fn(),
  updateNote: vi.fn(),
  deleteNote: vi.fn(),
  enrichNote: vi.fn(),
}));

afterEach(cleanup);

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
