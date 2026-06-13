import type { Mode, StandingRow } from "../types";
import { STRINGS, displayName } from "../i18n";
import { flag } from "../flags";

interface Props {
  groups: Record<string, StandingRow[]>;
  mode: Mode;
  focus: string[];
}

// Order groups so focus teams' groups come first.
function orderGroups(
  keys: string[],
  groups: Record<string, StandingRow[]>,
  focus: string[],
): string[] {
  const focusGroup = (g: string) =>
    groups[g]?.some((r) => focus.includes(r.team)) ? 0 : 1;
  return [...keys].sort(
    (a, b) => focusGroup(a) - focusGroup(b) || a.localeCompare(b),
  );
}

export function GroupStandings({ groups, mode, focus }: Props) {
  const t = STRINGS[mode];
  const keys = orderGroups(Object.keys(groups).sort(), groups, focus);

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
                <tr
                  key={r.team}
                  className={focus.includes(r.team) ? "focus-row" : ""}
                >
                  <td>
                    <span className="flag">{flag(r.team)}</span>
                    {displayName(r.team, mode)}
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
