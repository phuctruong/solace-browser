import type { AppModel } from "../types/App";
import { AppTile } from "./AppTile";

interface AppGridProps {
  apps: AppModel[];
  locked: boolean;
  connectedAppIds: string[];
  onOpen: (app: AppModel) => void;
  onRun: (app: AppModel) => void;
}

export function AppGrid({ apps, locked, connectedAppIds, onOpen, onRun }: AppGridProps): JSX.Element {
  return (
    <section className="app-grid">
      {apps.map((app) => {
        const isConnected = connectedAppIds.includes(app.id) || app.id === "solace";
        return (
          <AppTile
            key={app.id}
            app={{ ...app, status: isConnected ? "connected" : app.status }}
            locked={locked && app.id !== "solace"}
            onOpen={onOpen}
            onRun={onRun}
          />
        );
      })}
    </section>
  );
}
