import { describe, expect, it } from "vitest";
import type { ChatSourceReference } from "../types/chat";
import { shortExcerpt, uniqueSources } from "./sources";

function source(
  noteId: number,
  score: number,
  chunk = 0,
): ChatSourceReference {
  return {
    note_id: noteId,
    note_title: `Note ${noteId}`,
    chunk_index: chunk,
    source_hash: "h",
    score,
    excerpt: "text",
  };
}

describe("uniqueSources", () => {
  it("keeps one entry per note with the best score, in first-seen order", () => {
    const result = uniqueSources([
      source(2, 0.5, 0),
      source(1, 0.6, 0),
      source(2, 0.9, 1),
    ]);

    expect(result.map((s) => [s.note_id, s.score])).toEqual([
      [2, 0.9],
      [1, 0.6],
    ]);
  });
});

describe("shortExcerpt", () => {
  it("collapses whitespace and truncates long text", () => {
    expect(shortExcerpt("a \n  b")).toBe("a b");
    const long = shortExcerpt("x".repeat(500));
    expect(long.length).toBeLessThanOrEqual(161);
    expect(long.endsWith("…")).toBe(true);
  });
});
