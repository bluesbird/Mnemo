import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChatWorkspace } from "./ChatWorkspace";
import * as chatApi from "../api/chat";

Element.prototype.scrollIntoView = vi.fn();

afterEach(cleanup);

function renderChat(onMessagesChange = vi.fn()) {
  render(
    <ChatWorkspace
      messages={[]}
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
    const { box, onMessagesChange } = renderChat();

    fireEvent.change(box, { target: { value: "what is black?" } });
    fireEvent.keyDown(box, { key: "Enter" });

    expect(spy).toHaveBeenCalledWith({ question: "what is black?" });
    await waitFor(() => expect(onMessagesChange).toHaveBeenLastCalledWith([
      expect.objectContaining({ role: "user", text: "what is black?" }),
      expect.objectContaining({ role: "assistant", text: "ok", sources: [] }),
    ]));
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
