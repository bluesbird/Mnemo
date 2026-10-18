import { afterEach, describe, expect, it, vi } from "vitest";
import { enrichNote } from "./notes";

afterEach(() => vi.unstubAllGlobals());

describe("notes api", () => {
  it("explains when note enrichment is rate-limited", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 429 }) as Response),
    );

    await expect(enrichNote(1)).rejects.toThrow(/wait a moment/);
  });
});
