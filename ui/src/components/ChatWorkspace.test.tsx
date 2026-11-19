import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChatWorkspace } from "./ChatWorkspace";
import * as chatApi from "../api/chat";
import type { ChatMessage } from "../types/chat";

Element.prototype.scrollIntoView = vi.fn();

afterEach(cleanup);

function renderChat(
  onMessagesChange = vi.fn(),
  messages: ChatMessage[] = [],
) {
  render(
    <ChatWorkspace
      messages={messages}
      onMessagesChange={onMessagesChange}
      onOpenNote={vi.fn()}
    />,
  );
  return {
    onMessagesChange,
    box: screen.getByLabelText("Question for the chatbot"),
  };
}

describe("ChatWorkspace input", () => {
  it("explains that index operations are manual recovery tools", () => {
    renderChat();

    fireEvent.click(screen.getByText("Index ▾"));

    expect(screen.getByText(
      "Note changes sync automatically. These are manual recovery tools.",
    )).toBeTruthy();
  });

  it("opens a note with each distinct retrieved passage for that note", () => {
    const onOpenNote = vi.fn();
    const messages: ChatMessage[] = [{
      id: "answer",
      role: "assistant",
      text: "Here is the answer.",
      sources: [
        {
          note_id: 1,
          note_title: "Bluebird",
          chunk_index: 0,
          source_hash: "hash",
          score: 0.9,
          excerpt: "First passage",
          chunk_text: "First passage",
        },
        {
          note_id: 1,
          note_title: "Bluebird",
          chunk_index: 1,
          source_hash: "hash",
          score: 0.8,
          excerpt: "Second passage",
          chunk_text: "Second passage",
        },
        {
          note_id: 1,
          note_title: "Bluebird",
          chunk_index: 2,
          source_hash: "hash",
          score: 0.7,
          excerpt: "First passage",
          chunk_text: "First passage",
        },
        {
          note_id: 2,
          note_title: "Other note",
          chunk_index: 0,
          source_hash: "hash",
          score: 0.6,
          excerpt: "Other passage",
          chunk_text: "Other passage",
        },
      ],
    }];
    render(
      <ChatWorkspace
        messages={messages}
        onMessagesChange={vi.fn()}
        onOpenNote={onOpenNote}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Bluebird" }));

    expect(onOpenNote).toHaveBeenCalledWith(1, ["First passage", "Second passage"]);
    expect(screen.getByText("2 text chunks")).toBeTruthy();
  });

  it("shows a hint at the question limit and removes it after shortening", () => {
    const { box } = renderChat();
    expect(box.getAttribute("maxlength")).toBe("500");
    expect(screen.queryByText(/Question limit reached/)).toBeNull();
    fireEvent.change(box, { target: { value: "q".repeat(500) } });
    expect(screen.getByText("Question limit reached (500 characters).")).toBeTruthy();
    fireEvent.change(box, { target: { value: "q".repeat(499) } });
    expect(screen.queryByText(/Question limit reached/)).toBeNull();
  });

  it("sends on Enter", async () => {
    const spy = vi
      .spyOn(chatApi, "queryChat")
      .mockResolvedValue({ answer: "ok", sources: [] });
    const messages = [
      { id: "1", role: "user" as const, text: "Earlier question", sources: [] },
      { id: "2", role: "assistant" as const, text: "Earlier answer", sources: [] },
    ];
    const { box, onMessagesChange } = renderChat(vi.fn(), messages);

    fireEvent.change(box, { target: { value: "what is black?" } });
    fireEvent.keyDown(box, { key: "Enter" });

    expect(spy).toHaveBeenCalledWith({
      question: "what is black?",
      history: [
        { role: "user", content: "Earlier question" },
        { role: "assistant", content: "Earlier answer" },
      ],
    });
    await waitFor(() => expect(onMessagesChange).toHaveBeenLastCalledWith([
      ...messages,
      expect.objectContaining({ role: "user", text: "what is black?" }),
      expect.objectContaining({ role: "assistant", text: "ok", sources: [] }),
    ]));
  });

  it("does not include the retried question in its own history", async () => {
    const spy = vi
      .spyOn(chatApi, "queryChat")
      .mockResolvedValue({ answer: "ok", sources: [] });
    const messages: ChatMessage[] = [
      { id: "1", role: "user", text: "Earlier question", sources: [] },
      { id: "2", role: "assistant", text: "Earlier answer", sources: [] },
      { id: "3", role: "user", text: "Current question", sources: [] },
      {
        id: "4",
        role: "assistant",
        text: "Temporary failure",
        sources: [],
        isError: true,
      },
    ];
    renderChat(vi.fn(), messages);

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(spy).toHaveBeenCalledWith({
      question: "Current question",
      history: [
        { role: "user", content: "Earlier question" },
        { role: "assistant", content: "Earlier answer" },
      ],
    });
  });

  it.each([
    "summarize the chat",
    "Summarize what we discussed",
    "Pull together the main threads of our exchange",
    "Where do quokkas live?",
  ])("sends retained history without classifying '%s' in the UI", async (question) => {
    const spy = vi
      .spyOn(chatApi, "queryChat")
      .mockResolvedValue({ answer: "Summary.", sources: [] });
    const messages: ChatMessage[] = Array.from({ length: 12 }, (_, index) => ({
      id: String(index),
      role: index % 2 === 0 ? "user" : "assistant",
      text: `message ${index}`,
      sources: [],
    }));
    const { box } = renderChat(vi.fn(), messages);

    fireEvent.change(box, { target: { value: question } });
    fireEvent.keyDown(box, { key: "Enter" });

    expect(spy).toHaveBeenCalledWith({
      question,
      history: messages.map(({ role, text }) => ({ role, content: text })),
    });
  });

  it("caps history after excluding errors and shows the summary limit", async () => {
    const spy = vi
      .spyOn(chatApi, "queryChat")
      .mockResolvedValue({ answer: "Summary.", sources: [] });
    const messages: ChatMessage[] = Array.from({ length: 503 }, (_, index) => ({
      id: String(index),
      role: index % 2 === 0 ? "user" : "assistant",
      text: `message ${index}`,
      sources: [],
      isError: index === 501,
    }));
    const { box } = renderChat(vi.fn(), messages);

    expect(screen.getByText(/Only the latest 500 messages/)).toBeTruthy();
    fireEvent.change(box, { target: { value: "What have we covered so far?" } });
    fireEvent.keyDown(box, { key: "Enter" });

    expect(spy).toHaveBeenCalledWith({
      question: "What have we covered so far?",
      history: messages.filter((message) => !message.isError).slice(-500)
        .map(({ role, text }) => ({ role, content: text })),
    });
  });

  it("does not send on Shift+Enter", () => {
    const spy = vi.spyOn(chatApi, "queryChat");
    const { box } = renderChat();

    fireEvent.change(box, { target: { value: "line one" } });
    fireEvent.keyDown(box, { key: "Enter", shiftKey: true });

    expect(spy).not.toHaveBeenCalled();
  });

  it("does not send an empty question", () => {
    const spy = vi.spyOn(chatApi, "queryChat");
    const { box } = renderChat();

    fireEvent.keyDown(box, { key: "Enter" });

    expect(spy).not.toHaveBeenCalled();
  });
});
