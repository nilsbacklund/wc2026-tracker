import { useMemo, useState } from "react";
import type { Bracket as BracketData, Mode } from "../types";
import { STRINGS, displayName } from "../i18n";
import { flag } from "../flags";

interface Props {
  bracket: BracketData;
  mode: Mode;
  focus: string[];
}

// Knockout tree (which two matches' winners feed each later match).
const FEEDERS: Record<number, [number, number]> = {
  89: [74, 77], 90: [73, 75], 91: [76, 78], 92: [79, 80],
  93: [83, 84], 94: [81, 82], 95: [86, 88], 96: [85, 87],
  97: [89, 90], 98: [93, 94], 99: [91, 92], 100: [95, 96],
  101: [97, 98], 102: [99, 100],
  104: [101, 102],
};

// child match -> the match its winner feeds into (for walking a team's path).
const PARENT: Record<number, number> = {};
for (const [p, [a, b]] of Object.entries(FEEDERS)) {
  PARENT[a] = Number(p);
  PARENT[b] = Number(p);
}

// Column order chosen so each later match sits between its two feeders.
const COLUMNS: { key: string; matches: number[] }[] = [
  { key: "r32", matches: [74, 77, 73, 75, 83, 84, 81, 82, 76, 78, 79, 80, 86, 88, 85, 87] },
  { key: "r16", matches: [89, 90, 93, 94, 91, 92, 95, 96] },
  { key: "qf", matches: [97, 98, 99, 100] },
  { key: "sf", matches: [101, 102] },
  { key: "final", matches: [104] },
];

interface Resolved {
  home: string | null;
  away: string | null;
  winner: string | null;
}

export function Bracket({ bracket, mode, focus }: Props) {
  const t = STRINGS[mode];
  const [overrides, setOverrides] = useState<Record<number, string>>({});

  // Force a team to win every match on its path to the title (opponents stay
  // as the favorites) — the most-likely bracket in which that team wins.
  const makeWin = (team: string) => {
    const start = bracket.r32.find((r) => r.home === team || r.away === team);
    if (!start) return;
    const ov: Record<number, string> = {};
    let m: number | undefined = start.match;
    while (m != null) {
      ov[m] = team;
      m = PARENT[m];
    }
    setOverrides(ov);
  };

  // Focus teams that actually appear in the projected bracket.
  const winnable = focus.filter((tm) =>
    bracket.r32.some((r) => r.home === tm || r.away === tm),
  );

  const { results, champion, third } = useMemo(() => {
    const elo = bracket.elo;
    const seed: Record<number, [string | null, string | null]> = {};
    for (const r of bracket.r32) seed[r.match] = [r.home, r.away];

    const chalk = (a: string | null, b: string | null) =>
      a == null ? b : b == null ? a : (elo[a] ?? 0) >= (elo[b] ?? 0) ? a : b;

    const results: Record<number, Resolved> = {};
    const decide = (m: number, home: string | null, away: string | null) => {
      const ov = overrides[m];
      const winner = ov && (ov === home || ov === away) ? ov : chalk(home, away);
      results[m] = { home, away, winner };
    };

    for (const m of COLUMNS[0].matches) decide(m, seed[m]?.[0] ?? null, seed[m]?.[1] ?? null);
    for (const m of [89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 104]) {
      const [c1, c2] = FEEDERS[m];
      decide(m, results[c1]?.winner ?? null, results[c2]?.winner ?? null);
    }
    // Third place: losers of the two semifinals.
    const loser = (m: number) => {
      const r = results[m];
      if (!r) return null;
      return r.winner === r.home ? r.away : r.home;
    };
    const third = chalk(loser(101), loser(102));
    return { results, champion: results[104]?.winner ?? null, third };
  }, [bracket, overrides]);

  if (!bracket.r32.length) return null;

  const flip = (m: number, team: string | null) => {
    if (!team) return;
    setOverrides((o) => ({ ...o, [m]: team }));
  };

  const Team = ({ m, team }: { m: number; team: string | null }) => {
    const win = results[m]?.winner === team;
    return (
      <div
        className={`bracket-team${win ? " win" : team ? " out" : ""}`}
        onClick={() => flip(m, team)}
        title={team ?? ""}
      >
        {flag(team)} {team ? displayName(team, mode) : "—"}
      </div>
    );
  };

  return (
    <section className="panel">
      <h2 style={{ justifyContent: "space-between", flexWrap: "wrap" }}>
        <span>{t.bracketTitle}</span>
        <span style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
          {winnable.map((tm) => (
            <button key={tm} className="btn" onClick={() => makeWin(tm)}>
              🏆 {t.bracketMakeWin} {displayName(tm, mode)}
            </button>
          ))}
          {Object.keys(overrides).length > 0 && (
            <button className="btn" onClick={() => setOverrides({})}>
              {t.scenarioReset}
            </button>
          )}
        </span>
      </h2>
      <p className="subtle" style={{ marginTop: 0 }}>
        {t.bracketIntro}
      </p>

      <div className="bracket">
        {COLUMNS.map((col) => (
          <div className="bracket-col" key={col.key}>
            <h4>{t.rounds[col.key as keyof typeof t.rounds]}</h4>
            {col.matches.map((m) => (
              <div className="bracket-match" key={m}>
                <Team m={m} team={results[m]?.home ?? null} />
                <Team m={m} team={results[m]?.away ?? null} />
              </div>
            ))}
          </div>
        ))}
        <div className="bracket-col">
          <h4>{t.metrics.champ}</h4>
          <div className="bracket-champion">
            {flag(champion)} {champion ? displayName(champion, mode) : "—"}
          </div>
          <div className="subtle" style={{ textAlign: "center", fontSize: "0.7rem" }}>
            {t.thirdPlace}: {flag(third)} {third ? displayName(third, mode) : "—"}
          </div>
        </div>
      </div>
    </section>
  );
}
