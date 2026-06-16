import { useMemo } from "react";
import type { Metric, Mode, Snapshot } from "../types";
import { STRINGS, displayName } from "../i18n";
import { flag } from "../flags";

interface Props {
  snapshot: Snapshot;
  mode: Mode;
}

// The model's own most-likely bracket: greedily take the most probable team at
// each stage (champion by champ%, the other finalist by final%, then the two
// most likely remaining semifinalists, then four quarterfinalists), never
// reusing a team.
export function ModelPick({ snapshot, mode }: Props) {
  const t = STRINGS[mode];
  const probs = snapshot.probs;

  const pick = useMemo(() => {
    const byMetric = (m: Metric) =>
      Object.keys(probs).sort((a, b) => probs[b][m] - probs[a][m]);
    const used = new Set<string>();
    const take = (m: Metric, count: number) => {
      const out: string[] = [];
      for (const team of byMetric(m)) {
        if (used.has(team)) continue;
        used.add(team);
        out.push(team);
        if (out.length === count) break;
      }
      return out;
    };
    const champion = take("champ", 1)[0];
    const runnerUp = take("final", 1)[0];
    const semis = take("top4", 2);
    const quarters = take("qf", 4);
    return { champion, runnerUp, semis, quarters };
  }, [probs]);

  const Row = ({ label, team, metric }: { label: string; team: string; metric: Metric }) => (
    <div className="match">
      <span>
        <span className="subtle" style={{ marginRight: "0.6rem" }}>
          {label}
        </span>
        {flag(team)} {displayName(team, mode)}
      </span>
      <span className="subtle">{probs[team][metric].toFixed(1)}%</span>
    </div>
  );

  return (
    <section className="panel accent">
      <h2>🤖 {t.modelPickTitle}</h2>
      <p className="subtle" style={{ marginTop: 0 }}>
        {t.modelPickIntro}
      </p>
      <Row label={t.tierChampion} team={pick.champion} metric="champ" />
      <Row label={t.tierRunnerUp} team={pick.runnerUp} metric="final" />
      {pick.semis.map((tm) => (
        <Row key={tm} label={t.tierSemi} team={tm} metric="top4" />
      ))}
      {pick.quarters.map((tm) => (
        <Row key={tm} label={t.tierQuarter} team={tm} metric="qf" />
      ))}
    </section>
  );
}
