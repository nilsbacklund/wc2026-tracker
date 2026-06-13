import type { Metric, Mode, Snapshot } from "../types";
import { METRIC_ORDER, STRINGS } from "../i18n";
import { flag } from "../flags";

interface Props {
  snapshot: Snapshot;
  mode: Mode;
  limit?: number;
}

export function OddsTable({ snapshot, mode, limit = 16 }: Props) {
  const t = STRINGS[mode];
  const teams = Object.keys(snapshot.probs).sort(
    (a, b) => snapshot.probs[b].champ - snapshot.probs[a].champ,
  );
  const shown = teams.slice(0, limit);
  // Always include Sweden in Sverigeläge even if outside the top N.
  if (mode === "sv" && !shown.includes("Sweden") && teams.includes("Sweden")) {
    shown.push("Sweden");
  }

  return (
    <table>
      <thead>
        <tr>
          <th>{t.team}</th>
          {METRIC_ORDER.map((m: Metric) => (
            <th key={m}>{t.metrics[m]}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {shown.map((team) => {
          const p = snapshot.probs[team];
          return (
            <tr key={team} className={team === "Sweden" ? "sweden" : ""}>
              <td>
                <span className="flag">{flag(team)}</span>
                {team}
              </td>
              {METRIC_ORDER.map((m) => (
                <td key={m} className="bar-cell">
                  <div className="bar" style={{ width: `${p[m]}%` }} />
                  <span>{p[m].toFixed(1)}</span>
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
