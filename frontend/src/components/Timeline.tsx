import type { RunStep } from "../types/Run";
import { formatMs } from "../utils/formatting";

interface TimelineProps {
  steps: RunStep[];
}

export function Timeline({ steps }: TimelineProps): JSX.Element {
  return (
    <ol>
      {steps.map((step) => (
        <li key={step.id}>
          <strong>{step.name}</strong> · {step.action} · {step.status} · {formatMs(step.durationMs)} · {step.scope}
        </li>
      ))}
    </ol>
  );
}
