import { useEffect, useMemo, useState } from "react";
import type { Importance, Match, Mode, Snapshot, StandingRow } from "./types";
import { STRINGS } from "./i18n";
import {
  fetchHistory,
  fetchImportance,
  fetchLatestOdds,
  fetchMatches,
  fetchStandings,
} from "./api";
import { OddsTable } from "./components/OddsTable";
import { GroupStandings } from "./components/GroupStandings";
import { MatchList } from "./components/MatchList";
import { RaceChart } from "./components/RaceChart";
import { TeamFocus } from "./components/TeamFocus";
import { FocusPicker } from "./components/FocusPicker";
import { VitalMatches } from "./components/VitalMatches";
import { Tippningar } from "./components/Tippningar";
import { WhatIf } from "./components/WhatIf";
import { subscribeToSnapshots } from "./realtime";

type Appearance = "light" | "dark";

// When Supabase Realtime is configured, snapshot inserts push instantly and we
// poll only as a slow safety net. Without it, polling is the live mechanism.
const POLL_FAST_MS = 20000;
const POLL_BACKUP_MS = 120000;

function initialAppearance(): Appearance {
  const saved = localStorage.getItem("appearance");
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia?.("(prefers-color-scheme: light)").matches
    ? "light"
    : "dark";
}

export default function App() {
  const [mode, setMode] = useState<Mode>(
    () => (localStorage.getItem("mode") as Mode) || "sv",
  );
  const [appearance, setAppearance] = useState<Appearance>(initialAppearance);
  const [focusNeutral, setFocusNeutral] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("focus") || "[]");
    } catch {
      return [];
    }
  });
  const [latest, setLatest] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [standings, setStandings] = useState<Record<string, StandingRow[]>>({});
  const [importance, setImportance] = useState<Importance | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.mode = mode;
    root.dataset.appearance = appearance;
    root.lang = mode === "sv" ? "sv" : "en";
    localStorage.setItem("mode", mode);
    localStorage.setItem("appearance", appearance);
  }, [mode, appearance]);

  useEffect(() => {
    localStorage.setItem("focus", JSON.stringify(focusNeutral));
  }, [focusNeutral]);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const [l, h, m, s, imp] = await Promise.all([
          fetchLatestOdds(),
          fetchHistory(),
          fetchMatches(),
          fetchStandings(),
          fetchImportance().catch(() => null),
        ]);
        if (!active) return;
        setLatest(l);
        setHistory(h);
        setMatches(m);
        setStandings(s);
        setImportance(imp);
        setError(null);
      } catch (e) {
        if (active) setError(String(e));
      }
    };
    load();
    const unsubscribe = subscribeToSnapshots(load);
    const id = setInterval(load, unsubscribe ? POLL_BACKUP_MS : POLL_FAST_MS);
    return () => {
      active = false;
      clearInterval(id);
      unsubscribe?.();
    };
  }, []);

  const t = STRINGS[mode];

  // Sverigeläge always focuses Sweden; neutral uses the user's picks.
  const focus = mode === "sv" ? ["Sweden"] : focusNeutral;
  const allTeams = useMemo(
    () => (latest ? Object.keys(latest.probs) : []),
    [latest],
  );

  if (error && !latest) return <div className="error">⚠️ {error}</div>;
  if (!latest) return <div className="loading">…</div>;

  return (
    <div className="app">
      <header className="masthead">
        <div>
          <h1>{t.title}</h1>
          <p>{t.subtitle}</p>
        </div>
        <div className="controls">
          <button
            className="icon-btn"
            title={appearance === "dark" ? t.light : t.dark}
            aria-label={appearance === "dark" ? t.light : t.dark}
            onClick={() =>
              setAppearance(appearance === "dark" ? "light" : "dark")
            }
          >
            {appearance === "dark" ? "☀︎" : "☾"}
          </button>
          <button
            className="btn"
            onClick={() => setMode(mode === "sv" ? "neutral" : "sv")}
          >
            {t.modeToggle}
          </button>
        </div>
      </header>

      {mode === "sv" && (
        <TeamFocus
          team="Sweden"
          snapshot={latest}
          matches={matches}
          mode={mode}
          importance={importance}
        />
      )}

      {mode === "neutral" && (
        <>
          <FocusPicker
            focus={focusNeutral}
            allTeams={allTeams}
            mode={mode}
            onChange={setFocusNeutral}
          />
          {focusNeutral.map((team) => (
            <TeamFocus
              key={team}
              team={team}
              snapshot={latest}
              matches={matches}
              mode={mode}
              importance={importance}
            />
          ))}
        </>
      )}

      <Tippningar snapshot={latest} mode={mode} />

      {importance && <VitalMatches importance={importance} mode={mode} />}

      <WhatIf snapshot={latest} mode={mode} />

      <section className="panel">
        <h2>{t.raceTitle}</h2>
        <RaceChart
          history={history}
          latest={latest}
          matches={matches}
          mode={mode}
          focus={focus}
        />
      </section>

      <section className="panel">
        <h2>
          {t.oddsTable}
          <span className="subtle" style={{ fontWeight: 400 }}>
            {t.updated} {new Date(latest.ts).toLocaleString()}
          </span>
        </h2>
        <OddsTable snapshot={latest} mode={mode} focus={focus} />
      </section>

      <section className="panel">
        <h2>{t.matches}</h2>
        <MatchList matches={matches} mode={mode} />
      </section>

      <section className="panel">
        <h2>{t.standings}</h2>
        <GroupStandings groups={standings} mode={mode} focus={focus} />
      </section>
    </div>
  );
}
