import type { AppModel } from "../types/App";
import { formatTimestamp } from "../utils/formatting";

interface AppTileProps {
  app: AppModel;
  locked: boolean;
  onOpen: (app: AppModel) => void;
  onRun: (app: AppModel) => void;
}

export function AppTile({ app, locked, onOpen, onRun }: AppTileProps): JSX.Element {
  const status = locked ? "Locked" : app.status === "connected" ? "Connected" : app.status === "error" ? "Error" : "Ready";
  return (
    <article className={`app-tile ${locked ? "locked" : "unlocked"}`}>
      <button type="button" onClick={() => onOpen(app)} className="app-name" aria-label={`Open ${app.name}`}>
        <span>{app.icon}</span>
        <span>{app.name}</span>
      </button>
      <div className="badge">{status}</div>
      {app.description ? <p className="app-copy">{app.description}</p> : null}
      {app.lastRunTime || app.lastRunAt ? (
        <p className="app-meta">Last run {formatTimestamp(app.lastRunTime ?? app.lastRunAt ?? "")}</p>
      ) : (
        <p className="app-meta">No recent runs</p>
      )}
      <div>{app.budgetRemaining !== undefined ? `Budget ${app.budgetRemaining}` : "No budget"}</div>
      <button type="button" onClick={() => onRun(app)} disabled={locked || app.status !== "connected"}>
        Run Now
      </button>
    </article>
  );
}
