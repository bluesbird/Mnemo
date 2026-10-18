import type {
  ChatQueryRequest,
  ChatQueryResponse,
  IndexOperationResponse,
} from "../types/chat";

const CHAT_API_BASE_URL = (
  import.meta.env.VITE_MS2_API_BASE_URL ?? "/rag-api"
).replace(/\/$/, "");

function describeFailure(status: number, action: string): string {
  if (status === 429) {
    return `${action} was rate-limited. Please wait a moment and try again.`;
  }
  if (status === 422) return "Please enter a shorter, valid question.";
  if (status === 502 || status === 503 || status === 504) {
    return `${action} failed: a dependent service (notes or Ollama) is unavailable. Try again shortly.`;
  }
  if (status === 404) return `${action} failed: the chat service was not found.`;
  return `${action} failed (HTTP ${status}).`;
}

async function post<T>(
  path: string,
  action: string,
  body?: unknown,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${CHAT_API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error(`${action} failed: the chat service is not reachable.`);
  }

  if (!response.ok) throw new Error(describeFailure(response.status, action));
  return response.json() as Promise<T>;
}

export function queryChat(
  payload: ChatQueryRequest,
): Promise<ChatQueryResponse> {
  return post<ChatQueryResponse>("/api/v1/chat/query", "The question", payload);
}

export function reconcileIndex(): Promise<IndexOperationResponse> {
  return post<IndexOperationResponse>(
    "/api/v1/index/reconcile",
    "Reconcile",
  );
}

export function rebuildIndex(): Promise<IndexOperationResponse> {
  return post<IndexOperationResponse>("/api/v1/index/rebuild", "Rebuild");
}
