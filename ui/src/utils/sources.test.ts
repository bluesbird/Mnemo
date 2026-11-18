import { describe, expect, it } from "vitest";
import type { ChatSourceReference } from "../types/chat";
import { shortExcerpt, sourcePassagesForNote, uniqueSources } from "./sources";

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
    chunk_text: `Passage ${chunk}`,
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

describe("sourcePassagesForNote", () => {
  it("returns distinct chunk text for only the requested note", () => {
    const sources = [
      { ...source(2, 0.5, 0), chunk_text: "first passage" },
      { ...source(2, 0.4, 1), chunk_text: "second passage" },
      { ...source(2, 0.3, 2), chunk_text: "first passage" },
      { ...source(1, 0.8), chunk_text: "other note" },
    ];

    expect(sourcePassagesForNote(sources, 2)).toEqual([
      "first passage",
      "second passage",
    ]);
  });

  it("uses the displayed excerpt when an older citation has no chunk text", () => {
    const oldCitation = source(2, 0.5);
    delete oldCitation.chunk_text;

    expect(sourcePassagesForNote([oldCitation], 2)).toEqual(["text"]);
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
