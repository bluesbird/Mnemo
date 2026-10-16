import { useState } from "react";
import type { FormEvent } from "react";
import { queryChat } from "../api/chat";
import type { ChatMessage } from "../types/chat";

type ChatWorkspaceProps = {
  onOpenNote: (noteId: number) => void;
};

const EMPTY_MESSAGE =
  "Ask a question about your notes. I will answer using indexed note content from MS2.";

export function ChatWorkspace({ onOpenNote }: ChatWorkspaceProps) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isAsking, setIsAsking] = useState(false);

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isAsking) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: trimmed,
      sources: [],
    };

    setMessages((current) => [...current, userMessage]);
    setQuestion("");
    setIsAsking(true);

    try {
      const response = await queryChat({ question: trimmed });
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: response.answer,
        sources: response.sources,
      };
      setMessages((current) => [...current, assistantMessage]);
    } catch (cause) {
      const message =
        cause instanceof Error
          ? cause.message
          : "Could not get an answer from the chatbot.";
      setMessages((current) => [
        ...current,
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

  return (
    <section className="chat-workspace" aria-label="Chat workspace">
      <header className="chat-header">
        <p className="eyebrow">RAG CHAT</p>
        <h1>Ask your knowledge base</h1>
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
      </div>

      <form className="chat-form" onSubmit={(event) => void ask(event)}>
        <textarea
          aria-label="Question for the chatbot"
          placeholder="Ask about your notes…"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
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
