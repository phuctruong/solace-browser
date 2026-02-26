import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppGrid } from "../components/AppGrid";
import { ApprovalModal } from "../components/ApprovalModal";
import { RunsTable } from "../components/RunsTable";
import { EvidenceManager } from "../services/evidenceManager";
import { executeHeadless } from "../services/playwrightClient";
import { createApprovalRecord, syncEvidence } from "../services/solaceagiClient";
import { useSessionStore } from "../state/useSessionStore";
import type { AppModel } from "../types/App";
import type { ApprovalPreview } from "../types/Approval";
import type { RunModel } from "../types/Run";
import { APPS, SAMPLE_RUNS, STORAGE_KEYS } from "../utils/constants";
import { loadJson, saveJson } from "../utils/storage";

export function HomePage(): JSX.Element {
  const navigate = useNavigate();
  const session = useSessionStore((s) => s.session);
  const connectApp = useSessionStore((s) => s.connectApp);
  const [runs, setRuns] = useState<RunModel[]>(loadJson<RunModel[]>(STORAGE_KEYS.RUNS, SAMPLE_RUNS));
  const [pendingApp, setPendingApp] = useState<AppModel | null>(null);
  const [approvalOpen, setApprovalOpen] = useState(false);

  const locked = !session || !session.membershipTier;
  const connectedApps = session?.connectedApps ?? [];

  const preview: ApprovalPreview = useMemo(
    () => ({
      steps: 5,
      scopes: pendingApp?.scopes ?? [],
      estimatedCostUsd: 0.12,
      estimatedDurationSec: 18,
    }),
    [pendingApp],
  );

  function openApp(app: AppModel): void {
    if (locked && app.id === "solace") {
      navigate("/login");
      return;
    }
    if (locked) {
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

  async function onDecision(decision: "approve" | "override" | "cancel", reason?: string): Promise<void> {
    if (!pendingApp) {
      return;
    }
    await createApprovalRecord(preview, decision, reason);
    setApprovalOpen(false);
    if (decision === "cancel") {
      return;
    }

    const execution = await executeHeadless({
      appId: pendingApp.id,
      recipeId: `${pendingApp.id}.default`,
      seed: "phase-4.1",
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
      tokenCostUsd: 0.12,
      model: "L2/Sonnet",
      estimatedOpusUsd: 0.45,
      screenshots: execution.screenshots,
      steps: [
        {
          id: "1",
          name: "Execute recipe",
          action: "run",
          status: "success",
          durationMs: execution.durationMs,
          scope: pendingApp.scopes[0] ?? "browser.read",
        },
      ],
      firstHash: bundle.events[0]?.eventHash.slice(0, 6) ?? "",
      lastHash: bundle.events[bundle.events.length - 1]?.eventHash.slice(0, 6) ?? "",
      hashVerified: await evidence.verify(),
    };

    const nextRuns = [run, ...runs].slice(0, 20);
    setRuns(nextRuns);
    saveJson(STORAGE_KEYS.RUNS, nextRuns);
  }

  return (
    <section>
      <h2>Home</h2>
      {locked ? <p>Sign in to Solace to unlock apps</p> : <p>Apps unlocked and ready.</p>}
      <AppGrid apps={APPS} locked={locked} connectedAppIds={connectedApps} onOpen={openApp} onRun={requestRun} />
      <h3>Runs</h3>
      <RunsTable runs={runs} />
      <ApprovalModal open={approvalOpen} preview={preview} onDecision={onDecision} />
    </section>
  );
}
