import { startTransition, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppGrid } from "../components/AppGrid";
import { ApprovalModal } from "../components/ApprovalModal";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { RunsTable } from "../components/RunsTable";
import { EvidenceManager } from "../services/evidenceManager";
import { executeHeadless } from "../services/playwrightClient";
import {
  createApprovalRecord,
  getCreditsSummary,
  getRecentRuns,
  listInstalledApps,
  syncEvidence,
} from "../services/solaceagiClient";
import { useSessionStore } from "../state/useSessionStore";
import type { AppModel } from "../types/App";
import type { ApprovalPreview } from "../types/Approval";
import type { RunModel } from "../types/Run";
import { APPS, SAMPLE_RUNS, STORAGE_KEYS } from "../utils/constants";
import { formatUsd } from "../utils/formatting";
import { loadJson, saveJson } from "../utils/storage";

type PageState = "loading" | "loaded" | "error";

export function HomePage(): JSX.Element {
  const navigate = useNavigate();
  const session = useSessionStore((state) => state.session);
  const connectApp = useSessionStore((state) => state.connectApp);
  const [pageState, setPageState] = useState<PageState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [apps, setApps] = useState<AppModel[]>(APPS);
  const [creditsRemaining, setCreditsRemaining] = useState<number>(session?.creditsUsd ?? 0);
  const [runs, setRuns] = useState<RunModel[]>(() => {
    const storedRuns = loadJson<RunModel[]>(STORAGE_KEYS.RUNS, []);
    return storedRuns.length > 0 ? storedRuns : SAMPLE_RUNS;
  });
  const [pendingApp, setPendingApp] = useState<AppModel | null>(null);
  const [approvalOpen, setApprovalOpen] = useState(false);

  const locked = !session?.membershipTier;
  const connectedApps = session?.connectedApps ?? [];

  useEffect(() => {
    let active = true;

    async function loadDashboard(): Promise<void> {
      setPageState("loading");
      setError(null);
      try {
        const [installedApps, credits, recentRuns] = await Promise.all([
          listInstalledApps(),
          getCreditsSummary(),
          getRecentRuns(),
        ]);
        if (!active) {
          return;
        }
        startTransition(() => {
          setApps(installedApps);
          setCreditsRemaining(credits.remaining);
          setRuns(recentRuns);
          setPageState("loaded");
        });
      } catch (err) {
        if (!active) {
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
        setPageState("error");
      }
    }

    void loadDashboard();
    return () => {
      active = false;
    };
  }, [session?.uid]);

  const preview: ApprovalPreview = useMemo(
    () => ({
      steps: pendingApp?.scopeDetails
        ? pendingApp.scopeDetails.required.length + pendingApp.scopeDetails.optional.length + 2
        : 4,
      scopes: pendingApp?.scopes ?? [],
      estimatedCostUsd: pendingApp?.riskTier === "high" ? 0.28 : 0.12,
      estimatedDurationSec: pendingApp?.riskTier === "high" ? 22 : 16,
      taskId: pendingApp?.approvalTaskId,
      stepLabels: pendingApp
        ? [
            `Open ${pendingApp.name}`,
            "Capture page state",
            "Apply OAuth3 scopes",
            "Return evidence bundle",
          ]
        : [],
    }),
    [pendingApp],
  );

  function openApp(app: AppModel): void {
    if (!session && app.id === "solace") {
      navigate("/login");
      return;
    }
    if (locked && app.id !== "solace") {
      return;
    }

    if (!connectedApps.includes(app.id) && app.oauthUrl) {
      const popup = window.open(app.oauthUrl, "oauth", "width=520,height=700");
      if (!popup) {
        return;
      }
      const timer = window.setInterval(() => {
        if (popup.closed) {
          window.clearInterval(timer);
          connectApp(app.id);
        }
      }, 200);
      return;
    }

    navigate(`/app/${app.id}`);
  }

  function requestRun(app: AppModel): void {
    setPendingApp(app);
    setApprovalOpen(true);
  }

  async function handleDecision(decision: "approve" | "modify" | "abort", reason?: string): Promise<void> {
    if (!pendingApp) {
      return;
    }

    await createApprovalRecord(preview, decision, reason);
    if (decision !== "approve") {
      setApprovalOpen(false);
      if (decision === "abort") {
        setPendingApp(null);
      }
      return;
    }

    const execution = await executeHeadless({
      appId: pendingApp.id,
      recipeId: `${pendingApp.id}.default`,
      seed: "task-002",
      scopes: pendingApp.scopes,
    });

    const evidence = new EvidenceManager();
    await evidence.addEvent("RUN_REQUESTED", { app: pendingApp.id });
    await evidence.addEvent("RUN_COMPLETED", execution.output);
    const bundle = await evidence.buildBundle(`run_${Date.now()}`, pendingApp.id, execution.screenshots);
    await syncEvidence(bundle);

    const run: RunModel = {
      id: bundle.runId,
      appId: pendingApp.id,
      appName: pendingApp.name,
      status: execution.status,
      startedAt: new Date().toISOString(),
      durationMs: execution.durationMs,
      tokenCostUsd: preview.estimatedCostUsd,
      model: "L2/Sonnet",
      estimatedOpusUsd: 0.45,
      screenshots: execution.screenshots,
      steps: [
        {
          id: "step_1",
          name: `Run ${pendingApp.name}`,
          action: "run",
          status: "success",
          durationMs: execution.durationMs,
          scope: pendingApp.scopes[0] ?? "browser.read",
        },
      ],
      firstHash: bundle.events[0]?.eventHash.slice(0, 6) ?? "",
      lastHash: bundle.events[bundle.events.length - 1]?.eventHash.slice(0, 6) ?? "",
      hashVerified: await evidence.verify(),
      tokensConsumed: 912,
      modelLevel: "L2/Sonnet",
      savingsVsFullLlm: 0.33,
      evidence: execution.screenshots.map((shot) => ({
        src: `/evidence/${shot}`,
        label: shot,
      })),
    };

    const nextRuns = [run, ...runs].slice(0, 20);
    setRuns(nextRuns);
    saveJson(STORAGE_KEYS.RUNS, nextRuns);
    setApprovalOpen(false);
    setPendingApp(null);
  }

  return (
    <section className="dashboard-page">
      <div className="hero-panel">
        <div>
          <p className="eyebrow">Installed Apps</p>
          <h2>Home</h2>
          <p>{locked ? "Sign in to Solace to unlock apps" : "Apps unlocked and ready."}</p>
        </div>
        <div className="credits-card">
          <p className="eyebrow">Credits remaining</p>
          <strong>{formatUsd(creditsRemaining)}</strong>
          <p>{creditsRemaining.toFixed(2)}</p>
          <p>{session ? `${session.email}` : "Guest mode"}</p>
        </div>
      </div>

      {pageState === "loading" ? <LoadingSpinner /> : null}
      {pageState === "error" ? <p role="alert">Dashboard error: {error}</p> : null}

      {pageState !== "error" ? (
        <>
          {apps.length === 0 ? (
            <article className="empty-card">
              <h3>Install your first app</h3>
              <p>Connect a workspace, mailbox, or browser recipe to start creating replay-safe runs.</p>
              <button type="button" onClick={() => navigate("/store")}>
                Browse store
              </button>
            </article>
          ) : (
            <AppGrid apps={apps} locked={locked} connectedAppIds={connectedApps} onOpen={openApp} onRun={requestRun} />
          )}

          <section className="runs-section">
            <div className="section-header">
              <div>
                <p className="eyebrow">Recent runs</p>
                <h3>Runs</h3>
              </div>
              <p>{runs.length} stored execution records</p>
            </div>
            <RunsTable runs={runs} />
          </section>
        </>
      ) : null}

      <ApprovalModal
        open={approvalOpen}
        preview={preview}
        taskId={pendingApp?.approvalTaskId}
        onDecision={handleDecision}
        onClose={() => {
          setApprovalOpen(false);
          setPendingApp(null);
        }}
      />
    </section>
  );
}
