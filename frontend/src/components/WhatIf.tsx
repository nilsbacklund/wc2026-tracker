import { useEffect, useMemo, useRef, useState } from "react";
import type { Mode, Snapshot } from "../types";
import { STRINGS } from "../i18n";
import { simulate, fetchTeams, type TeamInfo } from "../api";
import { flag } from "../flags";

interface Props {
  snapshot: Snapshot;
  mode: Mode;
}

const ELO_RANGE = 300;

// Collapsible what-if panel: nudge a handful of teams' Elo and re-run the
// simulation server-side, showing the resulting champ%/advance% vs baseline.
export function WhatIf({ snapshot, mode }: Props) {
  const t = STRINGS[mode];
  const [open, setOpen] = useState(false);
  const [teams, setTeams] = useState<TeamInfo[]>([]);
  // team -> overridden Elo (only teams the user is adjusting)
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [result, setResult] = useState<Snapshot | null>(null);
  const [busy, setBusy] = useState(false);
  const debounce = useRef<number | undefined>(undefined);

  const baseElo = useMemo(() => {
    const map: Record<string, number> = {};
    for (const tm of teams) if (tm.elo != null) map[tm.name] = tm.elo;
    return map;
  }, [teams]);

  // Default selection: current top 6 by champ%, plus Sweden in sv mode.
  const defaultPicks = useMemo(() => {
    const ranked = Object.keys(snapshot.probs).sort(
      (a, b) => snapshot.probs[b].champ - snapshot.probs[a].champ,
    );
    const picks = ranked.slice(0, 6);
    if (mode === "sv" && !picks.includes("Sweden")) picks.push("Sweden");
    return picks;
  }, [snapshot, mode]);

  useEffect(() => {
    if (!open || teams.length) return;
    fetchTeams().then(setTeams).catch(() => {});
  }, [open, teams.length]);

  // Initialise sliders to baseline once teams + defaults are known.
  useEffect(() => {
    if (!teams.length || Object.keys(overrides).length) return;
    const init: Record<string, number> = {};
    for (const name of defaultPicks) {
      if (baseElo[name] != null) init[name] = baseElo[name];
    }
    setOverrides(init);
  }, [teams, defaultPicks, baseElo, overrides]);

  // Which overrides actually differ from baseline → send only those.
  const changed = useMemo(() => {
    const out: Record<string, number> = {};
    for (const [name, v] of Object.entries(overrides)) {
      if (baseElo[name] == null || Math.round(v) !== Math.round(baseElo[name])) {
        out[name] = v;
      }
    }
    return out;
  }, [overrides, baseElo]);

  // Debounced re-simulation when overrides change.
  useEffect(() => {
    if (!open) return;
    if (Object.keys(changed).length === 0) {
      setResult(null);
      return;
    }
    window.clearTimeout(debounce.current);
    debounce.current = window.setTimeout(() => {
      setBusy(true);
      simulate({ elo_overrides: changed, n_sims: 20000 })
        .then(setResult)
        .catch(() => {})
        .finally(() => setBusy(false));
    }, 400);
    return () => window.clearTimeout(debounce.current);
  }, [changed, open]);

  const reset = () => {
    const init: Record<string, number> = {};
    for (const name of Object.keys(overrides)) {
      if (baseElo[name] != null) init[name] = baseElo[name];
    }
    setOverrides(init);
    setResult(null);
  };

  const fmt = (n: number) => `${n.toFixed(1)}%`;
  const delta = (n: number) => `${n >= 0 ? "+" : ""}${n.toFixed(1)}`;

  return (
    <section className="panel">
      <h2 style={{ justifyContent: "space-between" }}>
        <span>{t.whatIf}</span>
        <button className="mode-toggle" onClick={() => setOpen(!open)}>
          {open ? t.hide : t.show}
        </button>
      </h2>
      {open && (
        <>
          <p style={{ color: "var(--muted)", fontSize: "0.82rem", marginTop: 0 }}>
            {t.whatIfIntro}
          </p>
          <table>
            <thead>
              <tr>
                <th>{t.whatIfPickTeams}</th>
                <th>{t.whatIfElo}</th>
                <th>{t.champion}</th>
                <th>{t.whatIfDelta}</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(overrides).map((name) => {
                const base = baseElo[name];
                const cur = overrides[name];
                const d = base != null ? cur - base : 0;
                const newP = result?.probs[name];
                const baseP = snapshot.probs[name];
                const dChamp =
                  newP && baseP ? newP.champ - baseP.champ : 0;
                return (
                  <tr key={name} className={name === "Sweden" ? "sweden" : ""}>
                    <td>
                      <span className="flag">{flag(name)}</span>
                      {name}
                    </td>
                    <td style={{ textAlign: "left" }}>
                      <input
                        type="range"
                        min={base != null ? base - ELO_RANGE : 1500}
                        max={base != null ? base + ELO_RANGE : 2300}
                        step={5}
                        value={Math.round(cur)}
                        disabled={base == null}
                        onChange={(e) =>
                          setOverrides((o) => ({
                            ...o,
                            [name]: Number(e.target.value),
                          }))
                        }
                        style={{ width: 130, verticalAlign: "middle" }}
                      />
                      <span style={{ marginLeft: 8 }}>
                        {Math.round(cur)}
                        {Math.abs(d) >= 1 && (
                          <span style={{ color: "var(--accent)" }}>
                            {" "}
                            ({delta(d)})
                          </span>
                        )}
                      </span>
                    </td>
                    <td>
                      {newP ? fmt(newP.champ) : baseP ? fmt(baseP.champ) : "—"}
                    </td>
                    <td
                      style={{
                        color:
                          dChamp > 0.05
                            ? "var(--pos)"
                            : dChamp < -0.05
                              ? "var(--neg)"
                              : "var(--muted)",
                      }}
                    >
                      {newP && baseP ? delta(dChamp) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div
            style={{
              marginTop: "0.8rem",
              display: "flex",
              alignItems: "center",
              gap: "1rem",
            }}
          >
            <button className="mode-toggle" onClick={reset}>
              {t.whatIfReset}
            </button>
            {busy && (
              <span style={{ color: "var(--muted)", fontSize: "0.82rem" }}>
                {t.whatIfSimulating}
              </span>
            )}
          </div>
        </>
      )}
    </section>
  );
}
