import { Link } from "react-router-dom";
import type { RunModel } from "../types/Run";
import { formatMs, formatTimestamp, formatUsd } from "../utils/formatting";

interface RunsTableProps {
  runs: RunModel[];
}

export function RunsTable({ runs }: RunsTableProps): JSX.Element {
  if (runs.length === 0) {
    return <p>No runs yet.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Run</th>
          <th>App</th>
          <th>Status</th>
          <th>Started</th>
          <th>Duration</th>
          <th>Cost</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr key={run.id}>
            <td>
              <Link to={`/run/${run.id}`}>{run.id}</Link>
            </td>
            <td>{run.appName}</td>
            <td>{run.status}</td>
            <td>{formatTimestamp(run.startedAt)}</td>
            <td>{formatMs(run.durationMs)}</td>
            <td>{formatUsd(run.tokenCostUsd)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
