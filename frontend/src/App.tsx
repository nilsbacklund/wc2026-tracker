import { useEffect, useState } from "react";
import type { Match, Mode, Snapshot, StandingRow } from "./types";
import { STRINGS } from "./i18n";
import {
  fetchHistory,
  fetchLatestOdds,
  fetchMatches,
  fetchStandings,
} from "./api";
import { OddsTable } from "./components/OddsTable";
import { GroupStandings } from "./components/GroupStandings";
import { MatchList } from "./components/MatchList";
import { RaceChart } from "./components/RaceChart";
import { SwedenPanel } from "./components/SwedenPanel";

// Poll interval — a local stand-in for Supabase Realtime, which will push
// snapshot rows in production. Swapping this for a realtime subscription
// later touches only this hook.
const POLL_MS = 20000;

export default function App() {
  const [mode, setMode] = useState<Mode>(
    () => (localStorage.getItem("mode") as Mode) || "sv",
  );
  const [latest, setLatest] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<Snapshot[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [standings, setStandings] = useState<Record<string, StandingRow[]>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.dataset.mode = mode;
    document.documentElement.lang = mode === "sv" ? "sv" : "en";
    localStorage.setItem("mode", mode);
  }, [mode]);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const [l, h, m, s] = await Promise.all([
          fetchLatestOdds(),
          fetchHistory(),
          fetchMatches(),
          fetchStandings(),
        ]);
        if (!active) return;
        setLatest(l);
        setHistory(h);
        setMatches(m);
        setStandings(s);
        setError(null);
      } catch (e) {
        if (active) setError(String(e));
      }
    };
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const t = STRINGS[mode];

  if (error && !latest) return <div className="error">⚠️ {error}</div>;
  if (!latest) return <div className="loading">…</div>;

  const swedenFirst = mode === "sv";

  return (
    <div className="app">
      <header className="masthead">
        <div>
          <h1>{t.title}</h1>
          <p>{t.subtitle}</p>
        </div>
        <button
          className="mode-toggle"
          onClick={() => setMode(mode === "sv" ? "neutral" : "sv")}
        >
          {t.modeToggle}
        </button>
      </header>

      {swedenFirst && <SwedenPanel snapshot={latest} matches={matches} />}

      <section className="panel">
        <h2>{t.raceTitle}</h2>
        <RaceChart history={history} latest={latest} mode={mode} />
      </section>

      <section className="panel">
        <h2>
          {t.oddsTable}
          <span style={{ color: "var(--muted)", fontSize: "0.7rem", fontWeight: 400 }}>
            {t.updated} {new Date(latest.ts).toLocaleString()}
          </span>
        </h2>
        <OddsTable snapshot={latest} mode={mode} />
      </section>

      <section className="panel">
        <h2>{t.matches}</h2>
        <MatchList matches={matches} mode={mode} />
      </section>

      <section className="panel">
        <h2>{t.standings}</h2>
        <GroupStandings groups={standings} mode={mode} />
      </section>
    </div>
  );
}
