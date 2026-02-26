import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { signInWithPopup } from "../../services/firebaseAuth";

describe("firebaseAuth.signInWithPopup", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns local fallback when popup is blocked", async () => {
    vi.spyOn(window, "open").mockReturnValue(null);
    const result = await signInWithPopup("gmail");
    expect(result.uid).toContain("uid_gmail_local");
  });

  it("uses github provider in fallback mode", async () => {
    vi.spyOn(window, "open").mockReturnValue(null);
    const result = await signInWithPopup("github");
    expect(result.email).toBe("github@example.com");
  });

  it("opens popup with expected auth url", async () => {
    vi.spyOn(window, "open").mockReturnValue(null);
    await signInWithPopup("gmail");
    expect(window.open).toHaveBeenCalledWith(
      "https://solaceagi.com/auth/browser-register",
      "solaceAuth",
      "width=480,height=720",
    );
  });

  it("resolves on valid auth message", async () => {
    const close = vi.fn();
    const popup = { close } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);

    const promise = signInWithPopup("gmail");

    window.dispatchEvent(
      new MessageEvent("message", {
        origin: "https://solaceagi.com",
        data: {
          type: "solace-auth-success",
          payload: {
            uid: "uid_remote",
            email: "remote@example.com",
            idToken: "idtok_remote",
          },
        },
      }),
    );

    await expect(promise).resolves.toEqual({
      uid: "uid_remote",
      email: "remote@example.com",
      idToken: "idtok_remote",
    });
    expect(close).toHaveBeenCalled();
  });

  it("ignores messages from different origins", async () => {
    const popup = { close: vi.fn() } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);
    vi.useFakeTimers();

    const promise = signInWithPopup("gmail");
    window.dispatchEvent(
      new MessageEvent("message", {
        origin: "https://evil.example",
        data: { type: "solace-auth-success", payload: { uid: "x", email: "x", idToken: "x" } },
      }),
    );

    vi.advanceTimersByTime(30_001);
    await expect(promise).rejects.toThrow("Auth popup timed out");
  });

  it("ignores unrelated message types", async () => {
    const popup = { close: vi.fn() } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);
    vi.useFakeTimers();

    const promise = signInWithPopup("gmail");
    window.dispatchEvent(
      new MessageEvent("message", {
        origin: "https://solaceagi.com",
        data: { type: "other-event" },
      }),
    );

    vi.advanceTimersByTime(30_001);
    await expect(promise).rejects.toThrow("Auth popup timed out");
  });

  it("rejects on timeout if no success message", async () => {
    const popup = { close: vi.fn() } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);
    vi.useFakeTimers();

    const promise = signInWithPopup("gmail");
    vi.advanceTimersByTime(30_001);

    await expect(promise).rejects.toThrow("Auth popup timed out");
  });

  it("keeps promise pending before timeout", async () => {
    const popup = { close: vi.fn() } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);
    vi.useFakeTimers();

    const settled = vi.fn();
    signInWithPopup("gmail").then(settled).catch(settled);
    vi.advanceTimersByTime(1_000);

    expect(settled).not.toHaveBeenCalled();
  });

  it("clears listener after success (no duplicate resolve)", async () => {
    const popup = { close: vi.fn() } as unknown as Window;
    vi.spyOn(window, "open").mockReturnValue(popup);

    const promise = signInWithPopup("gmail");

    const payload = {
      type: "solace-auth-success",
      payload: { uid: "u", email: "e", idToken: "t" },
    };

    window.dispatchEvent(new MessageEvent("message", { origin: "https://solaceagi.com", data: payload }));
    await expect(promise).resolves.toEqual({ uid: "u", email: "e", idToken: "t" });

    window.dispatchEvent(new MessageEvent("message", { origin: "https://solaceagi.com", data: payload }));
    expect(popup.close).toHaveBeenCalledTimes(1);
  });

  it("supports default provider argument", async () => {
    vi.spyOn(window, "open").mockReturnValue(null);
    const result = await signInWithPopup();
    expect(result.uid).toContain("uid_gmail_local");
  });
});
