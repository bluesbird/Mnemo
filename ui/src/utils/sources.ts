import type { ChatSourceReference } from "../types/chat";

const EXCERPT_LIMIT = 160;

// One entry per note: keeps the best-scoring chunk, ordered by first appearance.
export function uniqueSources(
  sources: ChatSourceReference[],
): ChatSourceReference[] {
  const byNote = new Map<number, ChatSourceReference>();
  for (const source of sources) {
    const existing = byNote.get(source.note_id);
    if (!existing || source.score > existing.score) {
      byNote.set(source.note_id, source);
    }
  }
  return [...byNote.values()];
}

export function shortExcerpt(text: string): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > EXCERPT_LIMIT
    ? `${flat.slice(0, EXCERPT_LIMIT).trimEnd()}…`
    : flat;
}
