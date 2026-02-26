export function formatUsd(value: number): string {
  return `$${value.toFixed(2)}`;
}

export function formatMs(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }
  return `${Math.round(ms / 1000)}s`;
}

export function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    hour12: false,
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function calcSavings(actualUsd: number, opusUsd: number): { saved: number; percent: number } {
  if (opusUsd <= 0) {
    return { saved: 0, percent: 0 };
  }
  const saved = Math.max(0, opusUsd - actualUsd);
  return {
    saved,
    percent: Math.round((saved / opusUsd) * 100),
  };
}
