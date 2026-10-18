import { afterEach, describe, expect, it, vi } from "vitest";
import { queryChat, reconcileIndex } from "./chat";

function mockFetch(response: Partial<Response> | Error) {
  const fn = vi.fn(async () => {
    if (response instanceof Error) throw response;
    return response as Response;
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("chat api", () => {
  it("posts the question and returns the parsed answer", async () => {
    const fetchMock = mockFetch({
      ok: true,
      status: 200,
      json: async () => ({ answer: "Hi", sources: [] }),
    });

    const result = await queryChat({ question: "hello" });

    expect(result.answer).toBe("Hi");
    expect(fetchMock).toHaveBeenCalledWith(
      "/rag-api/api/v1/chat/query",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ question: "hello" }),
      }),
    );
  });

  it("maps upstream failures to a friendly message", async () => {
    mockFetch({ ok: false, status: 502 });
    await expect(queryChat({ question: "x" })).rejects.toThrow(
      /unavailable/,
    );
  });

  it("reports an unreachable service", async () => {
    mockFetch(new TypeError("Failed to fetch"));
    await expect(queryChat({ question: "x" })).rejects.toThrow(
      /not reachable/,
    );
  });

  it("posts public index operations without credentials", async () => {
    const fetchMock = mockFetch({
      ok: true,
      status: 200,
      json: async () => ({
        indexed_note_ids: [],
        deleted_note_ids: [],
        skipped_note_ids: [],
        total_ms1_notes: 0,
      }),
    });

    await reconcileIndex();

    expect(fetchMock).toHaveBeenCalledWith(
      "/rag-api/api/v1/index/reconcile",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
