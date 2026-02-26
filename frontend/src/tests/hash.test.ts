import { describe, expect, it } from "vitest";
import { hashEvent, verifyHashChain } from "../utils/hash";

describe("hash chain", () => {
  it("verifies untampered chain", async () => {
    const e1 = await hashEvent("A", { ok: true }, "", "2026-02-26T10:00:00.000Z");
    const e2 = await hashEvent("B", { step: 2 }, e1.eventHash, "2026-02-26T10:00:01.000Z");

    expect(await verifyHashChain([e1, e2])).toBe(true);
  });

  it("fails verification when tampered", async () => {
    const e1 = await hashEvent("A", { ok: true }, "", "2026-02-26T10:00:00.000Z");
    const e2 = await hashEvent("B", { step: 2 }, e1.eventHash, "2026-02-26T10:00:01.000Z");
    const tampered = { ...e2, data: { step: 3 } };

    expect(await verifyHashChain([e1, tampered])).toBe(false);
  });
});
