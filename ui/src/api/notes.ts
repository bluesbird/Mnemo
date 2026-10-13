import type { Note, NoteDraft } from "../types/note";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(
  /\/$/,
  "",
);

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/v1/notes${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed (${response.status})`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function listNotes(): Promise<Note[]> {
  return request<Note[]>("");
}

export function createNote(draft: NoteDraft): Promise<Note> {
  return request<Note>("", { method: "POST", body: JSON.stringify(draft) });
}

export function updateNote(id: number, draft: NoteDraft): Promise<Note> {
  return request<Note>(`/${id}`, {
    method: "PUT",
    body: JSON.stringify(draft),
  });
}

export function deleteNote(id: number): Promise<void> {
  return request<void>(`/${id}`, { method: "DELETE" });
}

export function enrichNote(id: number): Promise<Note> {
  return request<Note>(`/${id}/ai-enrich`, { method: "POST" });
}