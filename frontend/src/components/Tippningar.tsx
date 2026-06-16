import { useMemo } from "react";
import type { Mode, Snapshot } from "../types";
import { STRINGS, displayName } from "../i18n";
import { flag } from "../flags";
import { TIPPNINGAR } from "../tippningar";

interface Props {
  snapshot: Snapshot;
  mode: Mode;
}

// Points awarded if a pick reaches the round it was slotted in.
const POINTS = { champ: 8, final: 5, top4: 3, qf: 2 } as const;

export function Tippningar({ snapshot, mode }: Props) {
  const t = STRINGS[mode];
  const probs = snapshot.probs;

  const ranked = useMemo(() => {
    const p = (team: string, metric: "champ" | "final" | "top4" | "qf") =>
      (probs[team]?.[metric] ?? 0) / 100;
    return TIPPNINGAR.map((tip) => {
      let exp = POINTS.champ * p(tip.champion, "champ");
      if (tip.runnerUp) exp += POINTS.final * p(tip.runnerUp, "final");
      for (const tm of tip.semis) exp += POINTS.top4 * p(tm, "top4");
      for (const tm of tip.quarters) exp += POINTS.qf * p(tm, "qf");
      return { tip, exp, champPct: probs[tip.champion]?.champ ?? 0 };
    }).sort((a, b) => b.exp - a.exp);
  }, [probs]);

  if (!ranked.length) return null;
  const maxExp = Math.max(...ranked.map((r) => r.exp), 0.01);

  return (
    <section className="panel">
      <h2>{t.tippTitle}</h2>
      <p className="subtle" style={{ marginTop: 0 }}>
        {t.tippIntro}
      </p>
      <div>
        {ranked.map(({ tip, exp, champPct }, i) => (
          <div
            key={tip.person}
            className={`lab-row${i === 0 ? " adjusted" : ""}`}
            style={{ alignItems: "center" }}
          >
            <span className="lab-rank">{i + 1}</span>
            <span className="lab-team" style={{ width: 96, fontWeight: 600 }}>
              {i === 0 ? "🥇 " : ""}
              {tip.person}
            </span>
            <span className="lab-track" style={{ maxWidth: 320 }}>
              <span
                className="lab-fill"
                style={{ width: `${(exp / maxExp) * 100}%` }}
              />
            </span>
            <span className="lab-val" style={{ width: 64 }}>
              {exp.toFixed(1)} p
            </span>
            <span
              className="subtle"
              style={{ flex: "1 1 auto", textAlign: "right" }}
            >
              {t.tippChampionPick}: {flag(tip.champion)}{" "}
              {displayName(tip.champion, mode)} ({champPct.toFixed(1)}%)
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
