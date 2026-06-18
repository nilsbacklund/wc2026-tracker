import { useMemo } from "react";
import type { Metric, Mode, Snapshot } from "../types";
import { STRINGS, displayName } from "../i18n";
import { flag } from "../flags";
import { modelBracket } from "../modelPick";

interface Props {
  snapshot: Snapshot;
  mode: Mode;
}

// The model's own most-likely bracket, rendered as a tiered list.
export function ModelPick({ snapshot, mode }: Props) {
  const t = STRINGS[mode];
  const probs = snapshot.probs;

  const pick = useMemo(() => modelBracket(probs), [probs]);

  const Row = ({ label, team, metric }: { label: string; team: string; metric: Metric }) => (
    <div className="match">
      <span>
        <span className="subtle" style={{ marginRight: "0.6rem" }}>
          {label}
        </span>
        {flag(team)} {displayName(team, mode)}
      </span>
      <span className="subtle">{probs[team][metric].toFixed(2)}%</span>
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
