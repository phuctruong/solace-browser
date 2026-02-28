import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApprovalModal } from "../components/ApprovalModal";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { createApprovalRecord, getAppManifest } from "../services/solaceagiClient";
import { useSessionStore } from "../state/useSessionStore";
import type { AppModel } from "../types/App";
import type { ApprovalPreview } from "../types/Approval";

type PageState = "loading" | "loaded" | "error";

export function AppDetailPage(): JSX.Element {
  const navigate = useNavigate();
  const { appId } = useParams<{ appId: string }>();
  const session = useSessionStore((state) => state.session);
  const setSession = useSessionStore((state) => state.setSession);
  const [pageState, setPageState] = useState<PageState>("loading");
  const [error, setError] = useState<string | null>(null);
  const [manifest, setManifest] = useState<AppModel | null>(null);
  const [showApproval, setShowApproval] = useState(false);

  useEffect(() => {
    let active = true;
    async function loadManifest(): Promise<void> {
      if (!appId) {
        setPageState("error");
        setError("Missing app id");
        return;
      }
      setPageState("loading");
      setError(null);
      try {
        const nextManifest = await getAppManifest(appId);
        if (!active) {
          return;
        }
        setManifest(nextManifest);
        setPageState("loaded");
      } catch (err) {
        if (!active) {
          return;
        }
        setError(err instanceof Error ? err.message : "Failed to load app manifest");
        setPageState("error");
      }
    }

    void loadManifest();
    return () => {
      active = false;
    };
  }, [appId]);

  const preview: ApprovalPreview = useMemo(
    () => ({
      steps: 4,
      scopes: manifest?.scopes ?? [],
      estimatedCostUsd: manifest?.riskTier === "high" ? 0.28 : 0.11,
      estimatedDurationSec: manifest?.riskTier === "high" ? 24 : 14,
      taskId: manifest?.approvalTaskId,
      stepLabels: ["Load app manifest", "Open connected surface", "Capture evidence", "Store replay data"],
    }),
    [manifest],
  );

  async function handleDecision(decision: "approve" | "modify" | "abort", reason?: string): Promise<void> {
    await createApprovalRecord(preview, decision, reason);
    setShowApproval(false);
  }

  function handleUninstall(): void {
    if (!manifest || !session) {
      return;
    }
    if (!window.confirm(`Uninstall ${manifest.name}?`)) {
      return;
    }
    setSession({
      ...session,
      connectedApps: session.connectedApps.filter((id) => id !== manifest.id),
    });
    navigate("/home");
  }

  return (
    <section className="detail-page">
      {pageState === "loading" ? <LoadingSpinner /> : null}
      {pageState === "error" ? <p role="alert">Manifest error: {error}</p> : null}

      {pageState === "loaded" && manifest ? (
        <>
          <div className="hero-panel">
            <div>
              <p className="eyebrow">{manifest.category}</p>
              <h2>{manifest.name}</h2>
              <p>{manifest.description}</p>
            </div>
            <div className={`risk-card risk-${manifest.riskTier ?? "low"}`}>
              <p className="eyebrow">Risk tier</p>
              <strong>{manifest.riskTier ?? "low"}</strong>
            </div>
          </div>

          <section className="detail-grid">
            <article className="detail-card">
              <h3>Scopes</h3>
              <table aria-label="Scopes">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Scopes</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="scope-required">
                    <td>Required</td>
                    <td>{manifest.scopeDetails?.required.join(", ") || "None"}</td>
                  </tr>
                  <tr className="scope-optional">
                    <td>Optional</td>
                    <td>{manifest.scopeDetails?.optional.join(", ") || "None"}</td>
                  </tr>
                  <tr className="scope-step-up">
                    <td>Step-up</td>
                    <td>{manifest.scopeDetails?.stepUp.join(", ") || "None"}</td>
                  </tr>
                </tbody>
              </table>
            </article>

            <article className="detail-card">
              <h3>Budget</h3>
              <p>Max reads: {manifest.budgets?.maxReads ?? 0}</p>
              <p>Max sends: {manifest.budgets?.maxSends ?? 0}</p>
              <p>Max deletes: {manifest.budgets?.maxDeletes ?? 0}</p>
            </article>
          </section>

          <div className="actions">
            <button type="button" onClick={() => setShowApproval(true)}>
              Run Now
            </button>
            <button type="button" onClick={handleUninstall}>
              Uninstall
            </button>
          </div>
        </>
      ) : null}

      <ApprovalModal
        open={showApproval}
        preview={preview}
        taskId={manifest?.approvalTaskId}
        onDecision={handleDecision}
        onClose={() => setShowApproval(false)}
      />
    </section>
  );
}
