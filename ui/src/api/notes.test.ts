import { afterEach, describe, expect, it, vi } from "vitest";
import { summarizeNote } from "./notes";

afterEach(() => vi.unstubAllGlobals());

describe("notes api", () => {
  it("calls the manual summarize endpoint", async () => {
    const note = { id: 1, summary: "This note records access details." };
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(note)));
    vi.stubGlobal("fetch", fetchMock);

    await expect(summarizeNote(1)).resolves.toEqual(note);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/api\/v1\/notes\/1\/summarize$/), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
  });

  it("shows the API detail when note summarization fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({
        title: "Note summarization failed",
        detail: "Note summarization reached its token limit before finishing. Please try again.",
      }), {
        status: 502,
        headers: { "Content-Type": "application/problem+json" },
      })),
    );

    await expect(summarizeNote(1)).rejects.toThrow(
      "Note summarization reached its token limit before finishing. Please try again.",
    );
  });

  it("explains when note summarization is rate-limited", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 429 }) as Response),
    );

    await expect(summarizeNote(1)).rejects.toThrow(/wait a moment/);
  });
});
