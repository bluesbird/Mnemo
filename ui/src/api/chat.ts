import type { ChatQueryRequest, ChatQueryResponse } from "../types/chat";
import type { IndexOperationResponse } from "../types/chat";

const CHAT_API_BASE_URL = (
  import.meta.env.VITE_MS2_API_BASE_URL ?? "/rag-api"
).replace(/\/$/, "");
const MS2_ADMIN_API_KEY = import.meta.env.VITE_MS2_ADMIN_API_KEY;

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

function adminHeaders(): HeadersInit {
  return {
    "Content-Type": "application/json",
    ...(MS2_ADMIN_API_KEY ? { "X-API-Key": MS2_ADMIN_API_KEY } : {}),
  };
}

async function postAdmin(path: string): Promise<IndexOperationResponse> {
  const response = await fetch(`${CHAT_API_BASE_URL}${path}`, {
    method: "POST",
    headers: adminHeaders(),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Admin request failed (${response.status})`);
  }

  return response.json() as Promise<IndexOperationResponse>;
}

export function reconcileIndex(): Promise<IndexOperationResponse> {
  return postAdmin("/api/v1/admin/index/reconcile");
}

export function rebuildIndex(): Promise<IndexOperationResponse> {
  return postAdmin("/api/v1/admin/index/rebuild");
}
