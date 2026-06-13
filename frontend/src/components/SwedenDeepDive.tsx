import { useEffect, useRef, useState } from "react";
import type { Match, Snapshot } from "../types";
import { METRIC_ORDER, STRINGS } from "../i18n";
import { simulate } from "../api";
import { flag } from "../flags";

interface Props {
  snapshot: Snapshot;
  matches: Match[];
}

type Outcome = "win" | "draw" | "loss";

// Hypothetical match override from Sweden's perspective, respecting the real
// home/away orientation (the engine reads score.home / score.away).
function hypoFor(m: Match, outcome: Outcome) {
  const swedenHome = m.home === "Sweden";
  const [swe, opp] =
    outcome === "win" ? [2, 0] : outcome === "draw" ? [1, 1] : [0, 2];
  const score = swedenHome
    ? { home: swe, away: opp }
    : { home: opp, away: swe };
  return { id: m.id, status: "finished" as const, score };
}

// The single Sweden section (Sverigeläge only): survival funnel across all
// rounds, the three group fixtures, and a "what must happen" scenario explorer.
export function SwedenDeepDive({ snapshot, matches }: Props) {
  const t = STRINGS.sv;
  const base = snapshot.probs["Sweden"];

  const groupMatches = matches.filter(
    (m) => m.stage === "group" && (m.home === "Sweden" || m.away === "Sweden"),
  );

  const [scenario, setScenario] = useState<Record<number, Outcome>>({});
  const [result, setResult] = useState<Snapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const debounce = useRef<number | undefined>(undefined);

  useEffect(() => {
    const chosen = Object.entries(scenario);
    if (chosen.length === 0) {
      setResult(null);
      return;
    }
    const hypotheticals = chosen
      .map(([id, oc]) => {
        const m = groupMatches.find((g) => g.id === Number(id));
        return m ? hypoFor(m, oc) : null;
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

  const scen = result?.probs["Sweden"];
  const maxVal = Math.max(...METRIC_ORDER.map((m) => base[m]), 1);
  const delta = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(1)}`;
  const deltaClass = (d: number) =>
    d > 0.05 ? "delta-pos" : d < -0.05 ? "delta-neg" : "";

  return (
    <section className="panel accent">
      <h2>
        {flag("Sweden")} {t.swedenRoute}
      </h2>

      {/* Survival funnel — advance through to champion */}
      <h3>{t.swedenSurvival}</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
        {METRIC_ORDER.map((m) => {
          const cur = scen ? scen[m] : base[m];
          return (
            <div
              key={m}
              style={{ display: "flex", alignItems: "center", gap: "0.7rem" }}
            >
              <span
                style={{
                  width: 130,
                  fontSize: "0.78rem",
                  color: "var(--muted)",
                  flex: "0 0 auto",
                }}
              >
                {t.metrics[m]}
              </span>
              <div
                style={{
                  flex: 1,
                  background: "var(--panel-2)",
                  borderRadius: 6,
                  height: 22,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${(cur / maxVal) * 100}%`,
                    background:
                      "linear-gradient(90deg, var(--bar-from), var(--bar-to))",
                    height: "100%",
                    borderRadius: 6,
                    transition: "width 0.4s ease",
                  }}
                />
              </div>
              <span
                style={{
                  width: 92,
                  textAlign: "right",
                  fontWeight: 700,
                  flex: "0 0 auto",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
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

      {/* Fixtures */}
      <h3 style={{ marginTop: "1.4rem" }}>{t.swedenFixtures}</h3>
      <div>
        {groupMatches.map((m) => {
          const opp = m.home === "Sweden" ? m.away : m.home;
          return (
            <div className="match" key={m.id}>
              <span>
                {flag("Sweden")} Sverige{" "}
                <span style={{ opacity: 0.5 }}>v</span> {opp} {flag(opp)}
              </span>
              <span className="subtle">
                {m.home_score != null ? (
                  <span className="score" style={{ color: "var(--text)" }}>
                    {m.home_score}–{m.away_score}
                  </span>
                ) : m.matchday ? (
                  `Omgång ${m.matchday}`
                ) : (
                  ""
                )}
              </span>
            </div>
          );
        })}
      </div>

      {/* Scenario explorer */}
      <h3 style={{ marginTop: "1.4rem" }}>{t.swedenScenario}</h3>
      <p className="subtle" style={{ marginTop: 0 }}>
        {t.swedenScenarioIntro}
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {groupMatches.map((m) => {
          const opp = m.home === "Sweden" ? m.away : m.home;
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
                {t.swedenVs} {flag(opp)} {opp}
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

      {/* Scenario outcome — only shown once a scenario is chosen */}
      {scen && (
        <div
          style={{ display: "flex", gap: "1rem", marginTop: "1rem", flexWrap: "wrap" }}
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
    </section>
  );
}
