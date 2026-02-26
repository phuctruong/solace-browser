import { create } from "zustand";
import { loadJson, removeItem, saveJson } from "../utils/storage";
import { STORAGE_KEYS } from "../utils/constants";

export interface SessionState {
  uid: string;
  email: string;
  apiKey: string;
  membershipTier?: string;
  creditsUsd: number;
  connectedApps: string[];
}

interface SessionStore {
  session: SessionState | null;
  setSession: (session: SessionState) => void;
  connectApp: (appId: string) => void;
  clearSession: () => void;
}

const initial = loadJson<SessionState | null>(STORAGE_KEYS.SESSION, null);

export const useSessionStore = create<SessionStore>((set, get) => ({
  session: initial,
  setSession: (session) => {
    saveJson(STORAGE_KEYS.SESSION, session);
    set({ session });
  },
  connectApp: (appId) => {
    const current = get().session;
    if (!current) {
      return;
    }
    const next = {
      ...current,
      connectedApps: Array.from(new Set([...current.connectedApps, appId])),
    };
    saveJson(STORAGE_KEYS.SESSION, next);
    set({ session: next });
  },
  clearSession: () => {
    removeItem(STORAGE_KEYS.SESSION);
    set({ session: null });
  },
}));
