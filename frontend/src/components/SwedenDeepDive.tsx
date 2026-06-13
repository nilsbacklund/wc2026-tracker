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

// Build a hypothetical match override from Sweden's perspective, respecting the
// real home/away orientation (the engine reads score.home / score.away).
function hypoFor(m: Match, outcome: Outcome) {
  const swedenHome = m.home === "Sweden";
  // Representative scorelines: win 2-0, draw 1-1, loss 0-2 (for Sweden).
  let swe = 0;
  let opp = 0;
  if (outcome === "win") [swe, opp] = [2, 0];
  else if (outcome === "draw") [swe, opp] = [1, 1];
  else [swe, opp] = [0, 2];
  const score = swedenHome
    ? { home: swe, away: opp }
    : { home: opp, away: swe };
  return { id: m.id, status: "finished" as const, score };
}

// Sweden deep-dive: round-by-round survival funnel + a "what must happen"
// scenario explorer over Sweden's three group matches. Sv mode only.
export function SwedenDeepDive({ snapshot, matches }: Props) {
  const t = STRINGS.sv;
  const base = snapshot.probs["Sweden"];

  const groupMatches = matches.filter(
    (m) =>
      m.stage === "group" && (m.home === "Sweden" || m.away === "Sweden"),
  );

  // outcome per match id; undefined = leave as-is (scheduled / real result).
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

  return (
    <section className="panel" style={{ borderColor: "var(--accent)" }}>
      <h2>
        {flag("Sweden")} {t.swedenDeepDive}
      </h2>

      <h3 style={{ fontSize: "0.85rem", margin: "0 0 0.6rem" }}>
        {t.swedenSurvival}
      </h3>
      <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
        {METRIC_ORDER.map((m) => (
          <div
            key={m}
            style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}
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
                position: "relative",
              }}
            >
              <div
                style={{
                  width: `${(base[m] / maxVal) * 100}%`,
                  background: "var(--accent)",
                  opacity: 0.85,
                  height: "100%",
                  borderRadius: 6,
                }}
              />
            </div>
            <span
              style={{
                width: 56,
                textAlign: "right",
                fontWeight: 700,
                flex: "0 0 auto",
              }}
            >
              {base[m].toFixed(1)}%
            </span>
          </div>
        ))}
      </div>

      <h3 style={{ fontSize: "0.85rem", margin: "1.3rem 0 0.3rem" }}>
        {t.swedenScenario}
      </h3>
      <p style={{ color: "var(--muted)", fontSize: "0.8rem", marginTop: 0 }}>
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
                      className="mode-toggle"
                      style={{
                        padding: "0.3rem 0.7rem",
                        fontSize: "0.78rem",
                        borderColor: active ? "var(--accent)" : "var(--border)",
                        background: active
                          ? "var(--accent-soft)"
                          : "transparent",
                      }}
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

      <div
        style={{ display: "flex", gap: "1rem", marginTop: "1rem", flexWrap: "wrap" }}
      >
        {(["advance", "champ"] as const).map((m) => (
          <div
            key={m}
            style={{
              flex: "1 1 160px",
              background: "var(--panel-2)",
              borderRadius: 8,
              padding: "0.7rem 0.9rem",
            }}
          >
            <div style={{ color: "var(--muted)", fontSize: "0.72rem" }}>
              {t.metrics[m]}
            </div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>
              {scen ? scen[m].toFixed(1) : base[m].toFixed(1)}%
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--muted)" }}>
              {t.whatIfBaseline} {base[m].toFixed(1)}%
              {scen && (
                <span
                  style={{
                    marginLeft: 6,
                    color:
                      scen[m] - base[m] > 0.05
                        ? "#4ade80"
                        : scen[m] - base[m] < -0.05
                          ? "var(--live)"
                          : "var(--muted)",
                  }}
                >
                  ({delta(scen[m] - base[m])})
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: "0.8rem",
          display: "flex",
          alignItems: "center",
          gap: "1rem",
        }}
      >
        <button
          className="mode-toggle"
          onClick={() => {
            setScenario({});
            setResult(null);
          }}
        >
          {t.scenarioReset}
        </button>
        {busy && (
          <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
            {t.whatIfSimulating}
          </span>
        )}
      </div>
    </section>
  );
}
