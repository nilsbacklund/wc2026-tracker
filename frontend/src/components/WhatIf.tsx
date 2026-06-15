import { useEffect, useMemo, useRef, useState } from "react";
import type { Metric, Mode, Snapshot } from "../types";
import { STRINGS, displayName } from "../i18n";
import { simulate, fetchTeams, type TeamInfo } from "../api";
import { flag } from "../flags";

interface Props {
  snapshot: Snapshot;
  mode: Mode;
}

const ADJUST_MAX = 300; // ± strength swing applied to a team's Elo
const LEADERBOARD = 12;
const METRICS: Metric[] = ["champ", "final", "top4", "advance"];

// Title Race Lab: boost or weaken any teams and watch the whole title-odds
// leaderboard re-rank live (server-side simulation, debounced).
export function WhatIf({ snapshot, mode }: Props) {
  const t = STRINGS[mode];
  const [open, setOpen] = useState(false);
  const [teams, setTeams] = useState<TeamInfo[]>([]);
  const [adjust, setAdjust] = useState<Record<string, number>>({});
  const [metric, setMetric] = useState<Metric>("champ");
  const [result, setResult] = useState<Snapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const debounce = useRef<number | undefined>(undefined);

  const baseElo = useMemo(() => {
    const map: Record<string, number> = {};
    for (const tm of teams) if (tm.elo != null) map[tm.name] = tm.elo;
    return map;
  }, [teams]);

  // Load the team roster (with base Elo) when first opened, and seed the
  // current favourite as a ready-to-drag adjuster.
  useEffect(() => {
    if (!open || teams.length) return;
    fetchTeams().then((ts) => {
      setTeams(ts);
      const fav = Object.keys(snapshot.probs).sort(
        (a, b) => snapshot.probs[b].champ - snapshot.probs[a].champ,
      )[0];
      if (fav) setAdjust((a) => (Object.keys(a).length ? a : { [fav]: 0 }));
    }).catch(() => {});
  }, [open, teams.length, snapshot]);

  const overrides = useMemo(() => {
    const out: Record<string, number> = {};
    for (const [name, d] of Object.entries(adjust)) {
      if (d !== 0 && baseElo[name] != null) out[name] = baseElo[name] + d;
    }
    return out;
  }, [adjust, baseElo]);

  useEffect(() => {
    if (!open) return;
    if (Object.keys(overrides).length === 0) {
      setResult(null);
      return;
    }
    window.clearTimeout(debounce.current);
    debounce.current = window.setTimeout(() => {
      setBusy(true);
      simulate({ elo_overrides: overrides, n_sims: 20000 })
        .then(setResult)
        .catch(() => {})
        .finally(() => setBusy(false));
    }, 350);
    return () => window.clearTimeout(debounce.current);
  }, [overrides, open]);

  const probs = result?.probs ?? snapshot.probs;
  const baseProbs = snapshot.probs;

  // Leaderboard: top N by the chosen metric, plus any adjusted team.
  const board = useMemo(() => {
    const ranked = Object.keys(probs).sort(
      (a, b) => probs[b][metric] - probs[a][metric],
    );
    const rankOf = new Map(ranked.map((tm, i) => [tm, i + 1]));
    const shown = ranked.slice(0, LEADERBOARD);
    for (const tm of Object.keys(adjust)) {
      if (!shown.includes(tm)) shown.push(tm);
    }
    const maxVal = Math.max(...shown.map((tm) => probs[tm][metric]), 1);
    return { rows: shown, rankOf, maxVal };
  }, [probs, metric, adjust]);

  const available = Object.keys(snapshot.probs)
    .filter((tm) => !(tm in adjust))
    .sort((a, b) => a.localeCompare(b));

  const setDelta = (team: string, d: number) =>
    setAdjust((a) => ({ ...a, [team]: d }));
  const remove = (team: string) =>
    setAdjust((a) => {
      const next = { ...a };
      delete next[team];
      return next;
    });
  const reset = () => {
    setAdjust({});
    setResult(null);
  };

  const arrow = (d: number) =>
    d > 0.05 ? "▲" : d < -0.05 ? "▼" : "";
  const dClass = (d: number) =>
    d > 0.05 ? "delta-pos" : d < -0.05 ? "delta-neg" : "subtle";

  return (
    <section className="panel">
      <h2 style={{ justifyContent: "space-between" }}>
        <span>{t.whatIf}</span>
        <button className="btn" onClick={() => setOpen(!open)}>
          {open ? t.hide : t.show}
        </button>
      </h2>

      {open && (
        <>
          <p className="subtle" style={{ marginTop: 0 }}>
            {t.whatIfIntro}
          </p>

          {/* adjusters */}
          <div style={{ marginBottom: "0.4rem" }}>
            {Object.keys(adjust).map((team) => {
              const d = adjust[team];
              return (
                <div className="lab-adjuster" key={team}>
                  <span className="name">
                    {flag(team)} {displayName(team, mode)}
                  </span>
                  <input
                    type="range"
                    min={-ADJUST_MAX}
                    max={ADJUST_MAX}
                    step={10}
                    value={d}
                    disabled={baseElo[team] == null}
                    onChange={(e) => setDelta(team, Number(e.target.value))}
                  />
                  <span className="amount">
                    <span className={d > 0 ? "delta-pos" : d < 0 ? "delta-neg" : "subtle"}>
                      {d > 0 ? "+" : ""}
                      {d}
                    </span>
                    {baseElo[team] != null && (
                      <span className="subtle"> · {Math.round(baseElo[team] + d)}</span>
                    )}
                  </span>
                  <button
                    className="lab-remove"
                    onClick={() => remove(team)}
                    aria-label="remove"
                  >
                    ×
                  </button>
                </div>
              );
            })}
            <select
              className="chip"
              value=""
              onChange={(e) => {
                if (e.target.value) setDelta(e.target.value, 0);
              }}
              style={{ appearance: "auto", marginTop: "0.4rem" }}
            >
              <option value="">+ {t.focusAdd}</option>
              {available.map((tm) => (
                <option key={tm} value={tm}>
                  {tm}
                </option>
              ))}
            </select>
          </div>

          {/* metric selector */}
          <div className="metric-tabs">
            {METRICS.map((m) => (
              <button
                key={m}
                className={`btn${metric === m ? " active" : ""}`}
                onClick={() => setMetric(m)}
              >
                {t.metrics[m]}
              </button>
            ))}
          </div>

          {/* live leaderboard */}
          <div>
            {board.rows.map((team) => {
              const val = probs[team][metric];
              const d = val - baseProbs[team][metric];
              return (
                <div
                  key={team}
                  className={`lab-row${team in adjust ? " adjusted" : ""}`}
                >
                  <span className="lab-rank">{board.rankOf.get(team)}</span>
                  <span className="lab-team">
                    {flag(team)} {displayName(team, mode)}
                  </span>
                  <span className="lab-track">
                    <span
                      className="lab-fill"
                      style={{ width: `${(val / board.maxVal) * 100}%` }}
                    />
                  </span>
                  <span className="lab-val">{val.toFixed(1)}%</span>
                  <span className={`lab-delta ${dClass(d)}`}>
                    {arrow(d)} {Math.abs(d) >= 0.05 ? Math.abs(d).toFixed(1) : ""}
                  </span>
                </div>
              );
            })}
          </div>

          <div
            style={{
              marginTop: "0.9rem",
              display: "flex",
              alignItems: "center",
              gap: "1rem",
            }}
          >
            <button className="btn" onClick={reset}>
              {t.whatIfReset}
            </button>
            {busy && <span className="subtle">{t.whatIfSimulating}</span>}
          </div>
        </>
      )}
    </section>
  );
}
