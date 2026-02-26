import { calcSavings, formatUsd } from "../utils/formatting";

interface CostSavingsWidgetProps {
  actualUsd: number;
  opusUsd: number;
  tokens: number;
  durationSec: number;
}

export function CostSavingsWidget({ actualUsd, opusUsd, tokens, durationSec }: CostSavingsWidgetProps): JSX.Element {
  const savings = calcSavings(actualUsd, opusUsd);
  return (
    <section>
      <p>
        Completed in {durationSec}s, {tokens} tokens
      </p>
      <p>Your cost: {formatUsd(actualUsd)}</p>
      <p>If you ran L3/Opus: {formatUsd(opusUsd)}</p>
      <p>
        Saved: {formatUsd(savings.saved)} ({savings.percent}% cheaper)
      </p>
      <p>ABCD testing found L2 works for this task</p>
    </section>
  );
}
