import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ChatWorkspace } from "./ChatWorkspace";
import * as chatApi from "../api/chat";

// jsdom does not implement scrollIntoView or crypto.randomUUID consistently.
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
  it("sends on Enter", async () => {
    const spy = vi
      .spyOn(chatApi, "queryChat")
      .mockResolvedValue({ answer: "ok", sources: [] });
    const { box } = renderChat();

    fireEvent.change(box, { target: { value: "what is black?" } });
    fireEvent.keyDown(box, { key: "Enter" });

    expect(spy).toHaveBeenCalledWith({ question: "what is black?" });
    await screen.findByLabelText("Question for the chatbot");
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
