import { useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { queryChat, rebuildIndex, reconcileIndex } from "../api/chat";
import type { ChatMessage, IndexOperationResponse } from "../types/chat";

type ChatWorkspaceProps = {
  messages: ChatMessage[];
  onMessagesChange: (messages: ChatMessage[]) => void;
  onOpenNote: (noteId: number) => void;
};

const EMPTY_MESSAGE =
  "Ask a question about your notes. I will answer using indexed note content from MS2.";

function summarizeAdminResult(
  operation: "reconcile" | "rebuild",
  result: IndexOperationResponse,
): string {
  return `${operation === "reconcile" ? "Reconcile" : "Rebuild"} complete · indexed ${result.indexed_note_ids.length}, deleted ${result.deleted_note_ids.length}, skipped ${result.skipped_note_ids.length}, total MS1 notes ${result.total_ms1_notes}.`;
}

export function ChatWorkspace({
  messages,
  onMessagesChange,
  onOpenNote,
}: ChatWorkspaceProps) {
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [isAdminActionRunning, setIsAdminActionRunning] = useState(false);
  const [adminFeedback, setAdminFeedback] = useState("");
  const threadEnd = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    threadEnd.current?.scrollIntoView({ block: "end" });
  }, [messages, isAsking]);

  useEffect(() => {
    if (!isAsking) textareaRef.current?.focus();
  }, [isAsking]);

  async function sendQuestion(text: string) {
    const trimmed = text.trim();
    if (!trimmed || isAsking) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: trimmed,
      sources: [],
    };
    const nextMessages = [...messages, userMessage];

    onMessagesChange(nextMessages);
    setQuestion("");
    await runQuery(trimmed, nextMessages);
  }

  async function retryLast() {
    const last = messages[messages.length - 1];
    const lastUser = messages[messages.length - 2];
    if (isAsking || !last?.isError || lastUser?.role !== "user") return;
    const base = messages.slice(0, -1);
    onMessagesChange(base);
    await runQuery(lastUser.text, base);
  }

  async function runQuery(trimmed: string, nextMessages: ChatMessage[]) {
    setIsAsking(true);

    try {
      const response = await queryChat({ question: trimmed });
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: response.answer,
        sources: response.sources,
      };
      onMessagesChange([...nextMessages, assistantMessage]);
    } catch (cause) {
      const message =
        cause instanceof Error
          ? cause.message
          : "Could not get an answer from the chatbot.";
      onMessagesChange([
        ...nextMessages,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: message,
          sources: [],
          isError: true,
        },
      ]);
    } finally {
      setIsAsking(false);
    }
  }

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await sendQuestion(question);
  }

  async function runAdminAction(operation: "reconcile" | "rebuild") {
    if (isAdminActionRunning || isAsking) return;
    if (
      operation === "rebuild" &&
      !window.confirm(
        "Rebuild the whole index? This re-embeds every note and can take a while.",
      )
    ) {
      return;
    }
    setIsAdminActionRunning(true);
    setAdminFeedback(
      operation === "rebuild"
        ? "Rebuilding index… this may take a while."
        : "Reconciling index…",
    );
    try {
      const result =
        operation === "reconcile" ? await reconcileIndex() : await rebuildIndex();
      setAdminFeedback(summarizeAdminResult(operation, result));
    } catch (cause) {
      setAdminFeedback(
        cause instanceof Error
          ? cause.message
          : "Admin action failed. Please check MS2 availability and API key.",
      );
    } finally {
      setIsAdminActionRunning(false);
    }
  }

  function startNewChat() {
    if (isAsking || isAdminActionRunning) return;
    onMessagesChange([]);
    setQuestion("");
    setAdminFeedback("");
  }

  function onQuestionKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      if (!isAsking && question.trim()) {
        void sendQuestion(question);
      }
    }
  }

  return (
    <section className="chat-workspace" aria-label="Chat workspace">
      <header className="chat-header">
        <p className="eyebrow">RAG CHAT</p>
        <h1>Ask your knowledge base</h1>
        <div className="chat-header-actions">
          <button
            type="button"
            className="text-button"
            disabled={isAsking || isAdminActionRunning}
            onClick={startNewChat}
          >
            New chat
          </button>
          <details className="index-menu">
            <summary>Index</summary>
            <div className="index-menu-items">
              <button
                type="button"
                className="text-button"
                disabled={isAsking || isAdminActionRunning}
                onClick={() => void runAdminAction("reconcile")}
              >
                Reconcile (sync changes)
              </button>
              <button
                type="button"
                className="text-button delete-button"
                disabled={isAsking || isAdminActionRunning}
                onClick={() => void runAdminAction("rebuild")}
              >
                Rebuild (re-embed all)
              </button>
            </div>
          </details>
        </div>
        <p className="chat-admin-feedback" role="status">
          {adminFeedback ||
            "Note changes may take a moment to appear in answers."}
        </p>
      </header>

      <div className="chat-thread" aria-live="polite">
        {messages.length === 0 && <p className="list-message">{EMPTY_MESSAGE}</p>}
        {messages.map((message) => (
          <article
            key={message.id}
            className={`chat-message chat-message-${message.role}${
              message.isError ? " chat-message-error" : ""
            }`}
          >
            <p className="chat-message-label">
              {message.role === "user" ? "You" : "Assistant"}
            </p>
            <p>{message.text}</p>
            {message.isError && message === messages[messages.length - 1] && (
              <button
                type="button"
                className="text-button"
                disabled={isAsking}
                onClick={() => void retryLast()}
              >
                Retry
              </button>
            )}
            {message.sources.length > 0 && (
              <div className="chat-sources">
                <p className="chat-sources-label">Sources</p>
                <ul>
                  {message.sources.map((source, index) => (
                    <li key={`${message.id}-${source.note_id}-${index}`}>
                      <button
                        type="button"
                        className="text-button"
                        onClick={() => onOpenNote(source.note_id)}
                      >
                        {source.note_title} (note #{source.note_id})
                      </button>
                      <p className="chat-source-excerpt">{source.excerpt}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </article>
        ))}
        {isAsking && <p className="list-message">Thinking…</p>}
        <div ref={threadEnd} />
      </div>

      <form className="chat-form" onSubmit={(event) => void ask(event)}>
        <textarea
          ref={textareaRef}
          aria-label="Question for the chatbot"
          placeholder="Ask about your notes…"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={onQuestionKeyDown}
          disabled={isAsking}
          required
        />
        <button className="save-button" type="submit" disabled={isAsking}>
          {isAsking ? "Asking…" : "Ask"}
        </button>
      </form>
    </section>
  );
}
