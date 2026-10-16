import type { ChatQueryRequest, ChatQueryResponse } from "../types/chat";

const CHAT_API_BASE_URL = (
  import.meta.env.VITE_MS2_API_BASE_URL ?? "/rag-api"
).replace(/\/$/, "");

export async function queryChat(
  payload: ChatQueryRequest,
): Promise<ChatQueryResponse> {
  const response = await fetch(`${CHAT_API_BASE_URL}/api/v1/chat/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Chat request failed (${response.status})`);
  }

  return response.json() as Promise<ChatQueryResponse>;
}
