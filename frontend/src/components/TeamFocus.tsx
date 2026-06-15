import { useEffect, useRef, useState } from "react";
import type { Importance, Match, Mode, Snapshot } from "../types";
import { METRIC_ORDER, STRINGS, displayName } from "../i18n";
import { simulate } from "../api";
import { flag } from "../flags";

interface Props {
  team: string;
  snapshot: Snapshot;
  matches: Match[];
  mode: Mode;
  importance?: Importance | null;
}

type Outcome = "win" | "draw" | "loss";

// Hypothetical override from the focus team's perspective, respecting the real
// home/away orientation (the engine reads score.home / score.away).
function hypoFor(m: Match, team: string, outcome: Outcome) {
  const home = m.home === team;
  const [mine, opp] =
    outcome === "win" ? [2, 0] : outcome === "draw" ? [1, 1] : [0, 2];
  const score = home ? { home: mine, away: opp } : { home: opp, away: mine };
  return { id: m.id, status: "finished" as const, score };
}

// Per-team focus panel: survival funnel across all rounds, the team's group
// fixtures, and a "what must happen" scenario explorer. Reused for Sweden in
// Sverigeläge and for any picked team in neutral mode.
export function TeamFocus({ team, snapshot, matches, mode, importance }: Props) {
  const t = STRINGS[mode];
  const base = snapshot.probs[team];

  const groupMatches = matches.filter(
    (m) => m.stage === "group" && (m.home === team || m.away === team),
  );

  const [scenario, setScenario] = useState<Record<number, Outcome>>({});
  const [result, setResult] = useState<Snapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const debounce = useRef<number | undefined>(undefined);

  // Reset the scenario if the focus team changes.
  useEffect(() => {
    setScenario({});
    setResult(null);
  }, [team]);

  useEffect(() => {
    const chosen = Object.entries(scenario);
    if (chosen.length === 0) {
      setResult(null);
      return;
    }
    const hypotheticals = chosen
      .map(([id, oc]) => {
        const m = groupMatches.find((g) => g.id === Number(id));
        return m ? hypoFor(m, team, oc) : null;
      })
      .filter((h): h is NonNullable<typeof h> => h !== null);
    window.clearTimeout(debounce.current);
    debounce.current = window.setTimeout(() => {
      setBusy(true);
      simulate({ hypotheticals, n_sims: 20000 })
        .then(setResult)
        .catch(() => {})
        .finally(() => setBusy(false));
    }, 400);
    return () => window.clearTimeout(debounce.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenario]);

  if (!base) return null;

  const name = displayName(team, mode);
  const scen = result?.probs[team];
  const maxVal = Math.max(...METRIC_ORDER.map((m) => base[m]), 1);
  const delta = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(1)}`;
  const deltaClass = (d: number) =>
    d > 0.05 ? "delta-pos" : d < -0.05 ? "delta-neg" : "";

  // Matches that swing this team's qualification odds the most (incl. rivals').
  const vital = (importance?.matches ?? [])
    .map((m) => ({ m, sw: m.teams[team]?.advance }))
    .filter((x) => x.sw)
    .map((x) => ({ ...x, swing: x.sw!.max - x.sw!.min }))
    .filter((x) => x.swing >= 0.5)
    .sort((a, b) => b.swing - a.swing)
    .slice(0, 5);

  return (
    <section className="panel accent">
      <h2>
        {flag(team)} {name}{" "}
        <span className="subtle" style={{ fontWeight: 400 }}>
          · {t.routeSuffix}
        </span>
      </h2>

      {/* survival funnel */}
      <h3>{t.roundByRound}</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
        {METRIC_ORDER.map((m) => {
          const cur = scen ? scen[m] : base[m];
          return (
            <div key={m} className="funnel-row">
              <span className="funnel-label">{t.metrics[m]}</span>
              <div className="funnel-track">
                <div
                  className="funnel-fill"
                  style={{ width: `${(cur / maxVal) * 100}%` }}
                />
              </div>
              <span className="funnel-value">
                {cur.toFixed(1)}%
                {scen && (
                  <span
                    className={deltaClass(scen[m] - base[m])}
                    style={{ fontSize: "0.72rem", marginLeft: 4 }}
                  >
                    {delta(scen[m] - base[m])}
                  </span>
                )}
              </span>
            </div>
          );
        })}
      </div>

      {/* fixtures */}
      <h3 style={{ marginTop: "1.4rem" }}>{t.fixtures}</h3>
      <div>
        {groupMatches.map((m) => {
          const opp = m.home === team ? m.away : m.home;
          return (
            <div className="match" key={m.id}>
              <span>
                {flag(team)} {name} <span style={{ opacity: 0.5 }}>{t.vs}</span>{" "}
                {opp} {flag(opp)}
              </span>
              <span className="subtle">
                {m.home_score != null ? (
                  <span className="score">
                    {m.home === team
                      ? `${m.home_score}–${m.away_score}`
                      : `${m.away_score}–${m.home_score}`}
                  </span>
                ) : m.matchday ? (
                  `${mode === "sv" ? "Omgång" : "MD"} ${m.matchday}`
                ) : (
                  ""
                )}
              </span>
            </div>
          );
        })}
      </div>

      {/* matches that matter most for this team */}
      {vital.length > 0 && (
        <>
          <h3 style={{ marginTop: "1.4rem" }}>
            {t.vitalFor} {name}
          </h3>
          <div>
            {vital.map(({ m, sw }) => (
              <div className="match" key={m.id}>
                <span>
                  {flag(m.home)} {displayName(m.home || "", mode)}{" "}
                  <span style={{ opacity: 0.5 }}>{t.vs}</span>{" "}
                  {displayName(m.away || "", mode)} {flag(m.away)}
                </span>
                <span className="subtle">
                  {t.metrics.advance}: {sw!.min.toFixed(0)}–{sw!.max.toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* scenario explorer */}
      {groupMatches.length > 0 && (
        <>
          <h3 style={{ marginTop: "1.4rem" }}>{t.scenario}</h3>
          <p className="subtle" style={{ marginTop: 0 }}>
            {t.scenarioIntro}
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {groupMatches.map((m) => {
              const opp = m.home === team ? m.away : m.home;
              return (
                <div
                  key={m.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "0.6rem",
                    flexWrap: "wrap",
                  }}
                >
                  <span style={{ fontSize: "0.85rem" }}>
                    {flag(opp)} {opp}
                  </span>
                  <div style={{ display: "flex", gap: "0.35rem" }}>
                    {(["win", "draw", "loss"] as Outcome[]).map((oc) => {
                      const active = scenario[m.id] === oc;
                      const label =
                        oc === "win"
                          ? t.resultWin
                          : oc === "draw"
                            ? t.resultDraw
                            : t.resultLoss;
                      return (
                        <button
                          key={oc}
                          className={`btn${active ? " active" : ""}`}
                          style={{ padding: "0.3rem 0.7rem", fontSize: "0.78rem" }}
                          onClick={() =>
                            setScenario((s) => {
                              const next = { ...s };
                              if (next[m.id] === oc) delete next[m.id];
                              else next[m.id] = oc;
                              return next;
                            })
                          }
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          {scen && (
            <div
              style={{
                display: "flex",
                gap: "1rem",
                marginTop: "1rem",
                flexWrap: "wrap",
              }}
            >
              {(["advance", "champ"] as const).map((m) => (
                <div key={m} className="stat-card" style={{ flex: "1 1 160px" }}>
                  <div className="label">{t.metrics[m]}</div>
                  <div className="value">{scen[m].toFixed(1)}%</div>
                  <div className="subtle">
                    {t.whatIfBaseline} {base[m].toFixed(1)}%{" "}
                    <span className={deltaClass(scen[m] - base[m])}>
                      ({delta(scen[m] - base[m])})
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div
            style={{
              marginTop: "1rem",
              display: "flex",
              alignItems: "center",
              gap: "1rem",
            }}
          >
            <button
              className="btn"
              onClick={() => {
                setScenario({});
                setResult(null);
              }}
            >
              {t.scenarioReset}
            </button>
            {busy && <span className="subtle">{t.whatIfSimulating}</span>}
          </div>
        </>
      )}
    </section>
  );
}
