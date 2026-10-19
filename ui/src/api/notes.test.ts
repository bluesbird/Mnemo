import { afterEach, describe, expect, it, vi } from "vitest";
import { enrichNote } from "./notes";

afterEach(() => vi.unstubAllGlobals());

describe("notes api", () => {
  it("shows the API detail when AI enrichment fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({
        title: "AI enrichment failed",
        detail: "AI enrichment reached its token limit before finishing. Please try again.",
      }), {
        status: 502,
        headers: { "Content-Type": "application/problem+json" },
      })),
    );

    await expect(enrichNote(1)).rejects.toThrow(
      "AI enrichment reached its token limit before finishing. Please try again.",
    );
  });

  it("explains when note enrichment is rate-limited", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 429 }) as Response),
    );

    await expect(enrichNote(1)).rejects.toThrow(/wait a moment/);
  });
});
