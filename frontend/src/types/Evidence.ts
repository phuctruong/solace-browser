export interface EvidenceEvent {
  timestamp: string;
  action: string;
  data: Record<string, unknown>;
  prevHash: string;
  eventHash: string;
}

export interface EvidenceBundle {
  runId: string;
  appId: string;
  events: EvidenceEvent[];
  screenshots: string[];
  manifestHash: string;
}
