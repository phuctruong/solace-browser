import type { RunStep } from "../types/Run";
import { formatMs } from "../utils/formatting";

interface TimelineProps {
  steps: RunStep[];
}

export function Timeline({ steps }: TimelineProps): JSX.Element {
  return (
    <ol className="timeline" aria-label="Run timeline">
      {steps.map((step) => (
        <li key={step.id} className={`timeline-step timeline-step-${step.status}`}>
          <strong>{step.name}</strong>
          <span>{step.status}</span>
          <span>{formatMs(step.durationMs)}</span>
          <span>{step.scope}</span>
        </li>
      ))}
    </ol>
  );
}
