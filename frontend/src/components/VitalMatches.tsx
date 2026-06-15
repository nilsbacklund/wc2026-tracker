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

  const ranked = useMemo(() => {
    return [...importance.matches]
      .sort((a, b) => b.total[metric] - a.total[metric])
      .slice(0, 8);
  }, [importance, metric]);

  if (!importance.matches.length) return null;
  const maxTotal = Math.max(...ranked.map((m) => m.total[metric]), 0.01);

  return (
    <section className="panel">
      <h2>{t.vitalMatches}</h2>
      <p className="subtle" style={{ marginTop: 0 }}>
        {t.vitalIntro}
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
          return (
            <div key={m.id} className="lab-row" style={{ alignItems: "stretch" }}>
              <span className="lab-team" style={{ width: 200 }}>
                {flag(m.home)} {m.home} <span className="subtle">v</span>{" "}
                {m.away} {flag(m.away)}
              </span>
              <span className="lab-track" style={{ alignSelf: "center" }}>
                <span
                  className="lab-fill"
                  style={{ width: `${(m.total[metric] / maxTotal) * 100}%` }}
                />
              </span>
              <span className="lab-val" style={{ width: 70 }}>
                {m.total[metric].toFixed(1)}
              </span>
              {mover && (
                <span
                  className="subtle"
                  style={{ width: 210, flex: "0 0 auto", textAlign: "right" }}
                >
                  {t.biggestMover}: {flag(mover.team)} {displayName(mover.team, mode)}{" "}
                  {mover.sw.min.toFixed(0)}–{mover.sw.max.toFixed(0)}%
                </span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
