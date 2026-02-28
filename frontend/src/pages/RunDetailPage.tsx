import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { CostSavingsWidget } from "../components/CostSavingsWidget";
import { EvidenceGallery } from "../components/EvidenceGallery";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { Timeline } from "../components/Timeline";
import { getRunDetail } from "../services/solaceagiClient";
import type { RunModel } from "../types/Run";
import { SAMPLE_RUNS, STORAGE_KEYS } from "../utils/constants";
import { loadJson } from "../utils/storage";

type PageState = "loading" | "loaded" | "error";

function resolveStoredRun(runId?: string): RunModel | null {
  const storedRuns = loadJson<RunModel[]>(STORAGE_KEYS.RUNS, []);
  if (storedRuns.length > 0) {
    return storedRuns.find((candidate) => candidate.id === runId) ?? storedRuns[0] ?? null;
  }
  if (!runId) {
    return SAMPLE_RUNS[0] ?? null;
  }
  return SAMPLE_RUNS.find((candidate) => candidate.id === runId) ?? SAMPLE_RUNS[0] ?? null;
}

export function RunDetailPage(): JSX.Element {
  const { runId } = useParams<{ runId: string }>();
  const fallbackRun = resolveStoredRun(runId);
  const [pageState, setPageState] = useState<PageState>(fallbackRun ? "loaded" : "loading");
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<RunModel | null>(fallbackRun);

  useEffect(() => {
    let active = true;

    async function loadRun(): Promise<void> {
      if (!runId) {
        setPageState("error");
        setError("Missing run id");
        return;
      }

      if (!fallbackRun) {
        setPageState("loading");
      }
      setError(null);
      try {
        const nextRun = await getRunDetail(runId);
        if (!active) {
          return;
        }
        setRun(nextRun);
        setPageState("loaded");
      } catch (err) {
        if (!active) {
          return;
        }
        if (!fallbackRun) {
          setError(err instanceof Error ? err.message : "Failed to load run detail");
          setPageState("error");
        }
      }
    }

    void loadRun();
    return () => {
      active = false;
    };
  }, [runId]);

  async function rerun(): Promise<void> {
    if (!runId) {
      return;
    }
    setPageState("loading");
    const nextRun = await getRunDetail(runId);
    setRun(nextRun);
    setPageState("loaded");
  }

  return (
    <section className="detail-page">
      {pageState === "loading" ? <LoadingSpinner /> : null}
      {pageState === "error" ? <p role="alert">Run error: {error}</p> : null}

      {run ? (
        <>
          <div className="hero-panel">
            <div>
              <p className="eyebrow">{run.appName}</p>
              <h2>Run Detail: {run.id}</h2>
              <p>Inspect every step, screenshot, cost, and replay verification artifact.</p>
            </div>
            <div className={`risk-card ${run.hashVerified ? "risk-low" : "risk-high"}`}>
              <p className="eyebrow">Verification</p>
              <strong>{run.hashVerified ? "Verified" : "Tampered"}</strong>
              <p>{run.hashVerified ? "Hash chain verified" : "Hash chain verification failed"}</p>
            </div>
          </div>

          <section className="detail-grid">
            <article className="detail-card">
              <h3>Timeline</h3>
              <Timeline steps={run.steps} />
            </article>

            <article className="detail-card">
              <h3>Evidence</h3>
              <EvidenceGallery screenshots={run.evidence ?? run.screenshots} />
            </article>
          </section>

          <section className="detail-grid">
            <article className="detail-card">
              <h3>Hash chain</h3>
              <p>First hash: {run.firstHash}</p>
              <p>Last hash: {run.lastHash}</p>
            </article>

            <article className="detail-card">
              <h3>Cost breakdown</h3>
              <p>Model level: {run.modelLevel ?? run.model}</p>
              <p>Tokens consumed: {run.tokensConsumed ?? 0}</p>
              <p>Cost: ${run.tokenCostUsd.toFixed(2)}</p>
              <p>Savings vs full LLM: ${(run.savingsVsFullLlm ?? 0).toFixed(2)}</p>
            </article>
          </section>

          <CostSavingsWidget
            actualUsd={run.tokenCostUsd}
            opusUsd={run.estimatedOpusUsd}
            tokens={run.tokensConsumed ?? 0}
            durationSec={Math.round(run.durationMs / 1000)}
          />

          <div className="actions">
            <button type="button" onClick={() => void rerun()}>
              Re-run
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}
