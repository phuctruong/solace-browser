import type { EvidenceEvent } from "../types/Evidence";

const encoder = new TextEncoder();

function toHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function sha256(input: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(input));
  return toHex(digest);
}

export async function hashEvent(
  action: string,
  data: Record<string, unknown>,
  prevHash: string,
  timestamp?: string,
): Promise<EvidenceEvent> {
  const event = {
    timestamp: timestamp ?? new Date().toISOString(),
    action,
    data,
    prevHash,
  };
  const eventHash = await sha256(JSON.stringify(event));
  return { ...event, eventHash };
}

export async function verifyHashChain(events: EvidenceEvent[]): Promise<boolean> {
  if (events.length === 0) {
    return true;
  }
  for (let i = 0; i < events.length; i += 1) {
    const event = events[i];
    if (i === 0 && event.prevHash !== "") {
      return false;
    }
    if (i > 0 && event.prevHash !== events[i - 1].eventHash) {
      return false;
    }
    const recomputed = await sha256(
      JSON.stringify({
        timestamp: event.timestamp,
        action: event.action,
        data: event.data,
        prevHash: event.prevHash,
      }),
    );
    if (recomputed !== event.eventHash) {
      return false;
    }
  }
  return true;
}
