import { useMemo, useState } from "react";
import type { ImpactMetric, Importance, MatchImpact, Mode } from "../types";
import { STRINGS, displayName } from "../i18n";
import { flag } from "../flags";

interface Props {
  importance: Importance;
  mode: Mode;
}

// The team whose odds swing most across a match's outcomes, for a metric.
function biggestMover(m: MatchImpact, metric: ImpactMetric) {
  let best: { team: string; swing: number; sw: { min: number; max: number } } | null = null;
  for (const [team, sw] of Object.entries(m.teams)) {
    const swing = sw[metric].max - sw[metric].min;
    if (!best || swing > best.swing) best = { team, swing, sw: sw[metric] };
  }
  return best;
}

export function VitalMatches({ importance, mode }: Props) {
  const t = STRINGS[mode];
  const [metric, setMetric] = useState<ImpactMetric>("advance");
  const [open, setOpen] = useState<number | null>(null);

  const ranked = useMemo(() => {
    return [...importance.matches]
      .sort((a, b) => b.total[metric] - a.total[metric])
      .slice(0, 8);
  }, [importance, metric]);

  if (!importance.matches.length) return null;
  const maxTotal = Math.max(...ranked.map((m) => m.total[metric]), 0.01);
  const suffix = metric === "advance" ? "adv" : "champ";

  // Each participant's odds under win / draw / loss (from their perspective).
  function breakdown(m: MatchImpact, side: "home" | "away") {
    const by = Object.fromEntries(m.outcomes.map((o) => [o.label, o]));
    const v = (label: string) => {
      const o = by[label];
      return o ? (o as never)[`${side}_${suffix}`] as number : null;
    };
    const winLabel = side === "home" ? "home" : "away";
    const lossLabel = side === "home" ? "away" : "home";
    return { win: v(winLabel), draw: v("draw"), loss: v(lossLabel) };
  }

  return (
    <section className="panel">
      <h2>{t.vitalMatches}</h2>
      <p className="subtle" style={{ marginTop: 0 }}>
        {t.vitalIntro} {t.vitalExpandHint}
      </p>
      <div className="metric-tabs">
        {(["advance", "champ"] as ImpactMetric[]).map((m) => (
          <button
            key={m}
            className={`btn${metric === m ? " active" : ""}`}
            onClick={() => setMetric(m)}
          >
            {t.metrics[m]}
          </button>
        ))}
      </div>
      <div>
        {ranked.map((m) => {
          const mover = biggestMover(m, metric);
          const isOpen = open === m.id;
          const sides: ("home" | "away")[] = ["home", "away"];
          return (
            <div key={m.id}>
              <div
                className="lab-row"
                style={{ alignItems: "center", cursor: "pointer" }}
                onClick={() => setOpen(isOpen ? null : m.id)}
              >
                <span style={{ width: 14, color: "var(--muted)" }}>
                  {isOpen ? "▾" : "▸"}
                </span>
                <span className="lab-team" style={{ width: 196 }}>
                  {flag(m.home)} {m.home} <span className="subtle">v</span>{" "}
                  {m.away} {flag(m.away)}
                </span>
                <span className="lab-track" style={{ alignSelf: "center" }}>
                  <span
                    className="lab-fill"
                    style={{ width: `${(m.total[metric] / maxTotal) * 100}%` }}
                  />
                </span>
                <span className="lab-val" style={{ width: 64 }}>
                  {m.total[metric].toFixed(2)}
                </span>
                {mover && (
                  <span
                    className="subtle"
                    style={{ width: 200, flex: "0 0 auto", textAlign: "right" }}
                  >
                    {t.biggestMover}: {flag(mover.team)}{" "}
                    {displayName(mover.team, mode)} {mover.sw.min.toFixed(0)}–
                    {mover.sw.max.toFixed(0)}%
                  </span>
                )}
              </div>

              {isOpen && (
                <div
                  style={{
                    margin: "0.2rem 0 0.8rem 1.6rem",
                    padding: "0.6rem 0.8rem",
                    background: "var(--panel-2)",
                    borderRadius: 8,
                  }}
                >
                  <table style={{ fontSize: "0.82rem" }}>
                    <thead>
                      <tr>
                        <th>{t.metrics[metric]} %</th>
                        <th>{t.resultWin}</th>
                        <th>{t.resultDraw}</th>
                        <th>{t.resultLoss}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sides.map((side) => {
                        const team = side === "home" ? m.home : m.away;
                        const b = breakdown(m, side);
                        const cell = (x: number | null) =>
                          x == null ? "–" : x.toFixed(metric === "champ" ? 2 : 1);
                        return (
                          <tr key={side}>
                            <td>
                              {flag(team)} {displayName(team || "", mode)}
                            </td>
                            <td>{cell(b.win)}</td>
                            <td>{cell(b.draw)}</td>
                            <td>{cell(b.loss)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
