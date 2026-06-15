import { useMemo } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  TimeScale,
  Tooltip,
  Legend,
} from "chart.js";
import "chartjs-adapter-date-fns";
import type { Match, Mode, Snapshot } from "../types";
import { STRINGS } from "../i18n";
import { flag } from "../flags";

ChartJS.register(LineElement, PointElement, LinearScale, TimeScale, Tooltip, Legend);

const COLORS = [
  "#5b8cff", "#f06595", "#46d39a", "#c77dff",
  "#ff9f40", "#36cfd1", "#ffd000", "#9aa7c2",
];

const DAY = 86400000;

interface Props {
  history: Snapshot[];
  latest: Snapshot;
  matches: Match[];
  mode: Mode;
  focus: string[];
}

export function RaceChart({ history, latest, matches, mode, focus }: Props) {
  const t = STRINGS[mode];
  const css = getComputedStyle(document.documentElement);
  const muted = css.getPropertyValue("--muted").trim() || "#9aa7c2";
  const text = css.getPropertyValue("--text").trim() || "#eef2fb";
  const accent = css.getPropertyValue("--accent").trim() || "#ffc83d";

  const { datasets, hasData } = useMemo(() => {
    const byId = new Map(matches.map((m) => [m.id, m]));
    const kickoffs = matches
      .map((m) => (m.kickoff_utc ? new Date(m.kickoff_utc).getTime() : NaN))
      .filter((n) => !isNaN(n));
    const firstKickoff = kickoffs.length ? Math.min(...kickoffs) : Date.now();

    // One point per match: the pre-tournament baseline + each full-time
    // snapshot, placed on the timeline at the match's kickoff.
    const points = history
      .filter((s) => s.trigger === "pretournament" || s.trigger === "fulltime")
      .map((s) => {
        let x: number;
        if (s.trigger === "pretournament" || s.match_id == null) {
          x = firstKickoff - DAY; // baseline sits just before kick-off
        } else {
          const m = byId.get(s.match_id);
          x = m?.kickoff_utc ? new Date(m.kickoff_utc).getTime() : firstKickoff;
        }
        return { x, probs: s.probs };
      })
      .sort((a, b) => a.x - b.x);

    const ranked = Object.keys(latest.probs).sort(
      (a, b) => latest.probs[b].champ - latest.probs[a].champ,
    );
    const picks = ranked.slice(0, 6);
    for (const f of focus) if (!picks.includes(f)) picks.push(f);

    const datasets = picks.map((team, i) => {
      const isFocus = focus.includes(team);
      const color = isFocus ? accent : COLORS[i % COLORS.length];
      return {
        label: `${flag(team)} ${team}`,
        data: points.map((p) => ({ x: p.x, y: p.probs[team]?.champ ?? null })),
        borderColor: color,
        backgroundColor: color,
        borderWidth: isFocus ? 3 : 2,
        tension: 0.3,
        pointRadius: points.length <= 16 ? 3 : 0,
        pointHoverRadius: 5,
      };
    });
    return { datasets, hasData: points.length >= 2 };
  }, [history, latest, matches, mode, focus, accent]);

  if (!hasData) {
    return <p className="loading">{t.noHistory}</p>;
  }

  return (
    <div className="chart-wrap">
      <Line
        data={{ datasets }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "nearest", intersect: false },
          scales: {
            x: {
              type: "time",
              time: { unit: "day", tooltipFormat: "PP" },
              ticks: { color: muted, maxRotation: 0, autoSkipPadding: 24 },
              grid: { display: false },
            },
            y: {
              beginAtZero: true,
              title: { display: true, text: `${t.champion} %`, color: muted },
              ticks: { color: muted, callback: (v) => `${v}%` },
              grid: { color: "rgba(128,128,128,0.16)" },
            },
          },
          plugins: {
            legend: { labels: { color: text, usePointStyle: true, boxWidth: 8 } },
            tooltip: {
              callbacks: {
                label: (ctx) =>
                  `${ctx.dataset.label}: ${Number(ctx.parsed.y).toFixed(1)}%`,
              },
            },
          },
        }}
      />
    </div>
  );
}
