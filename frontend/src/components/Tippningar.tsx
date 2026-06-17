import { useMemo } from "react";
import type { Mode, Snapshot } from "../types";
import { STRINGS, displayName } from "../i18n";
import { flag } from "../flags";
import { TIPPNINGAR, type Tippning } from "../tippningar";
import { modelBracket } from "../modelPick";

interface Props {
  snapshot: Snapshot;
  mode: Mode;
}

export function Tippningar({ snapshot, mode }: Props) {
  const t = STRINGS[mode];
  const probs = snapshot.probs;

  const ranked = useMemo(() => {
    // Family scoring: +1 per picked team that reaches the round it's placed in
    // (a pick at tier T is implicitly predicted to reach QF/SF/Final up to T),
    // +2 for the correct champion, +1 for the correct runner-up. A certain
    // champion therefore scores QF+SF+Final (3) + 2 = 5.
    const p = (team: string, metric: "champ" | "final" | "top4" | "qf") =>
      (probs[team]?.[metric] ?? 0) / 100;
    const score = (tip: Tippning) => {
      const c = tip.champion;
      // champion: reaches QF, SF, Final + winner bonus
      let exp = p(c, "qf") + p(c, "top4") + p(c, "final") + 2 * p(c, "champ");
      if (tip.runnerUp) {
        const r = tip.runnerUp;
        // runner-up: reaches QF, SF, Final + bonus for being exactly 2nd
        exp += p(r, "qf") + p(r, "top4") + p(r, "final");
        exp += p(r, "final") - p(r, "champ"); // P(exactly runner-up)
      }
      for (const tm of tip.semis) exp += p(tm, "qf") + p(tm, "top4");
      for (const tm of tip.quarters) exp += p(tm, "qf");
      return exp;
    };

    // The model competes too, as a benchmark entry.
    const mb = modelBracket(probs);
    const modelTip: Tippning = {
      person: t.modelName,
      champion: mb.champion,
      runnerUp: mb.runnerUp,
      semis: mb.semis,
      quarters: mb.quarters,
    };

    const entries = [
      ...TIPPNINGAR.map((tip) => ({ tip, isModel: false })),
      { tip: modelTip, isModel: true },
    ].map(({ tip, isModel }) => ({
      tip,
      isModel,
      exp: score(tip),
      champPct: probs[tip.champion]?.champ ?? 0,
    }));
    entries.sort((a, b) => b.exp - a.exp);
    const topHuman = entries.find((e) => !e.isModel);
    return entries.map((e) => ({ ...e, isLeader: e === topHuman }));
  }, [probs, t.modelName]);

  if (!ranked.length) return null;
  const maxExp = Math.max(...ranked.map((r) => r.exp), 0.01);

  return (
    <section className="panel">
      <h2>{t.tippTitle}</h2>
      <p className="subtle" style={{ marginTop: 0 }}>
        {t.tippIntro}
      </p>
      <div>
        {ranked.map(({ tip, exp, champPct, isModel, isLeader }, i) => (
          <div
            key={tip.person}
            className={`lab-row${isModel ? " adjusted" : ""}`}
            style={{ alignItems: "center" }}
          >
            <span className="lab-rank">{i + 1}</span>
            <span className="lab-team" style={{ width: 110, fontWeight: 600 }}>
              {isModel ? "🤖 " : isLeader ? "🥇 " : ""}
              {tip.person}
            </span>
            <span className="lab-track" style={{ maxWidth: 300 }}>
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
