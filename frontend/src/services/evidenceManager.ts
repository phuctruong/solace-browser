import type { EvidenceBundle, EvidenceEvent } from "../types/Evidence";
import { hashEvent, sha256, verifyHashChain } from "../utils/hash";

export class EvidenceManager {
  private events: EvidenceEvent[] = [];

  async addEvent(action: string, data: Record<string, unknown>): Promise<EvidenceEvent> {
    const prevHash = this.events.length > 0 ? this.events[this.events.length - 1].eventHash : "";
    const event = await hashEvent(action, data, prevHash);
    this.events.push(event);
    return event;
  }

  async buildBundle(runId: string, appId: string, screenshots: string[]): Promise<EvidenceBundle> {
    const manifestHash = await sha256(
      JSON.stringify({ runId, appId, eventCount: this.events.length, screenshots }),
    );
    return {
      runId,
      appId,
      events: this.events,
      screenshots,
      manifestHash,
    };
  }

  async verify(): Promise<boolean> {
    return verifyHashChain(this.events);
  }

  getEvents(): EvidenceEvent[] {
    return this.events;
  }
}
