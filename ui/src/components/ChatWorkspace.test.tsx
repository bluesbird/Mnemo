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
