import { useMemo } from "react";
import { useParams } from "react-router-dom";
import type { RunModel } from "../types/Run";
import { STORAGE_KEYS, SAMPLE_RUNS } from "../utils/constants";
import { loadJson } from "../utils/storage";
import { RunsTable } from "../components/RunsTable";

export function AppDetailPage(): JSX.Element {
  const { appId } = useParams<{ appId: string }>();
  const runs = loadJson<RunModel[]>(STORAGE_KEYS.RUNS, SAMPLE_RUNS);

  const filtered = useMemo(() => runs.filter((run) => run.appId === appId), [runs, appId]);

  return (
    <section>
      <h2>App Detail: {appId}</h2>
      <RunsTable runs={filtered} />
    </section>
  );
}
