import { useParams } from "react-router-dom";
import { CostSavingsWidget } from "../components/CostSavingsWidget";
import { EvidenceGallery } from "../components/EvidenceGallery";
import { Timeline } from "../components/Timeline";
import type { RunModel } from "../types/Run";
import { SAMPLE_RUNS, STORAGE_KEYS } from "../utils/constants";
import { loadJson } from "../utils/storage";

export function RunDetailPage(): JSX.Element {
  const { runId } = useParams<{ runId: string }>();
  const runs = loadJson<RunModel[]>(STORAGE_KEYS.RUNS, SAMPLE_RUNS);
  const run = runs.find((item) => item.id === runId) ?? SAMPLE_RUNS[0];

  return (
    <section>
      <h2>Run Detail: {run.id}</h2>
      <Timeline steps={run.steps} />
      <EvidenceGallery screenshots={run.screenshots} />
      <p>
        {run.hashVerified
          ? `Hash chain verified. First: ${run.firstHash}, Last: ${run.lastHash}`
          : "Hash chain verification failed"}
      </p>
      <CostSavingsWidget
        actualUsd={run.tokenCostUsd}
        opusUsd={run.estimatedOpusUsd}
        tokens={847}
        durationSec={Math.round(run.durationMs / 1000)}
      />
    </section>
  );
}
