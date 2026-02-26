import { describe, expect, it } from "vitest";
import { EvidenceManager } from "../../services/evidenceManager";

describe("EvidenceManager", () => {
  it("starts with empty events", () => {
    const manager = new EvidenceManager();
    expect(manager.getEvents()).toHaveLength(0);
  });

  it("adds first event with empty prev hash", async () => {
    const manager = new EvidenceManager();
    const event = await manager.addEvent("START", { a: 1 });
    expect(event.prevHash).toBe("");
  });

  it("chains second event to first hash", async () => {
    const manager = new EvidenceManager();
    const first = await manager.addEvent("A", {});
    const second = await manager.addEvent("B", {});
    expect(second.prevHash).toBe(first.eventHash);
  });

  it("buildBundle includes run and app metadata", async () => {
    const manager = new EvidenceManager();
    await manager.addEvent("A", {});
    const bundle = await manager.buildBundle("run_1", "gmail", ["shot.png"]);
    expect(bundle.runId).toBe("run_1");
    expect(bundle.appId).toBe("gmail");
  });

  it("buildBundle includes manifest hash", async () => {
    const manager = new EvidenceManager();
    await manager.addEvent("A", {});
    const bundle = await manager.buildBundle("run_1", "gmail", []);
    expect(bundle.manifestHash.length).toBeGreaterThan(10);
  });

  it("verify returns true on untampered chain", async () => {
    const manager = new EvidenceManager();
    await manager.addEvent("A", { x: 1 });
    await manager.addEvent("B", { y: 2 });
    await expect(manager.verify()).resolves.toBe(true);
  });

  it("verify returns true for empty chain", async () => {
    const manager = new EvidenceManager();
    await expect(manager.verify()).resolves.toBe(true);
  });

  it("getEvents returns added events in order", async () => {
    const manager = new EvidenceManager();
    await manager.addEvent("FIRST", {});
    await manager.addEvent("SECOND", {});
    expect(manager.getEvents().map((e) => e.action)).toEqual(["FIRST", "SECOND"]);
  });
});
