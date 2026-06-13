import type { Metric, Mode, Snapshot } from "../types";
import { METRIC_ORDER, STRINGS, displayName } from "../i18n";
import { flag } from "../flags";

interface Props {
  snapshot: Snapshot;
  mode: Mode;
  focus: string[];
  limit?: number;
}

export function OddsTable({ snapshot, mode, focus, limit = 16 }: Props) {
  const t = STRINGS[mode];
  const teams = Object.keys(snapshot.probs).sort(
    (a, b) => snapshot.probs[b].champ - snapshot.probs[a].champ,
  );
  const shown = teams.slice(0, limit);
  // Always include focus teams, even if outside the top N.
  for (const f of focus) {
    if (!shown.includes(f) && teams.includes(f)) shown.push(f);
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
            <tr key={team} className={focus.includes(team) ? "focus-row" : ""}>
              <td>
                <span className="flag">{flag(team)}</span>
                {displayName(team, mode)}
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
