import type { Mode, StandingRow } from "../types";
import { STRINGS } from "../i18n";
import { flag } from "../flags";

interface Props {
  groups: Record<string, StandingRow[]>;
  mode: Mode;
}

// Sverigeläge shows Sweden's group (F) first.
function orderGroups(keys: string[], mode: Mode): string[] {
  if (mode !== "sv") return keys;
  return [...keys].sort((a, b) => (a === "F" ? -1 : b === "F" ? 1 : a.localeCompare(b)));
}

export function GroupStandings({ groups, mode }: Props) {
  const t = STRINGS[mode];
  const keys = orderGroups(Object.keys(groups).sort(), mode);

  return (
    <div className="grid">
      {keys.map((g) => (
        <div key={g} className="group-card">
          <strong>
            {t.group} {g}
          </strong>
          <table>
            <thead>
              <tr>
                <th>{t.team}</th>
                <th>{t.played}</th>
                <th>+/-</th>
                <th>P</th>
              </tr>
            </thead>
            <tbody>
              {groups[g].map((r) => (
                <tr key={r.team} className={r.team === "Sweden" ? "sweden" : ""}>
                  <td>
                    <span className="flag">{flag(r.team)}</span>
                    {r.team}
                  </td>
                  <td>{r.played}</td>
                  <td>{r.gd > 0 ? `+${r.gd}` : r.gd}</td>
                  <td>{r.pts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
