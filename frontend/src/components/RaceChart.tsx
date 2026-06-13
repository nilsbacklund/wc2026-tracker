import { useMemo } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend,
} from "chart.js";
import type { Match, Mode, Snapshot } from "../types";
import { STRINGS } from "../i18n";
import { flag } from "../flags";

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Legend);

// Distinct line colors; Sweden always gets the theme yellow.
const COLORS = [
  "#5b8cff", "#f06595", "#46d39a", "#c77dff",
  "#ff9f40", "#36cfd1", "#ffd000", "#9aa7c2",
];

interface Props {
  history: Snapshot[];
  latest: Snapshot;
  matches: Match[];
  mode: Mode;
  focus: string[];
}

// Short label for a snapshot's triggering match, e.g. "🇲🇽 2–0 🇿🇦".
function pointLabel(s: Snapshot, byId: Map<number, Match>, mode: Mode): string {
  if (s.trigger === "pretournament" || s.match_id == null) {
    return mode === "sv" ? "Start" : "Start";
  }
  const m = byId.get(s.match_id);
  if (!m) return `#${s.match_id}`;
  const score =
    m.home_score != null ? `${m.home_score}–${m.away_score}` : "v";
  return `${flag(m.home)}${score}${flag(m.away)}`;
}

export function RaceChart({ history, latest, matches, mode, focus }: Props) {
  const t = STRINGS[mode];
  const css = getComputedStyle(document.documentElement);
  const muted = css.getPropertyValue("--muted").trim() || "#9aa7c2";
  const text = css.getPropertyValue("--text").trim() || "#eef2fb";
  const accent = css.getPropertyValue("--accent").trim() || "#ffc83d";
  const gridColor =
    css.getPropertyValue("--appearance-grid").trim() || "rgba(128,128,128,0.18)";

  const { labels, datasets } = useMemo(() => {
    const byId = new Map(matches.map((m) => [m.id, m]));
    // One point per match event: the pre-tournament baseline + result snapshots.
    const points = history.filter(
      (s) => s.trigger === "pretournament" || s.match_id != null,
    );
    const labels = points.map((s) => pointLabel(s, byId, mode));

    const ranked = Object.keys(latest.probs).sort(
      (a, b) => latest.probs[b].champ - latest.probs[a].champ,
    );
    const picks = ranked.slice(0, 6);
    // Always include focus teams, highlighted with the theme accent.
    for (const f of focus) if (!picks.includes(f)) picks.push(f);

    const datasets = picks.map((team, i) => {
      const isFocus = focus.includes(team);
      const color = isFocus ? accent : COLORS[i % COLORS.length];
      return {
        label: `${flag(team)} ${team}`,
        data: points.map((s) => s.probs[team]?.champ ?? null),
        borderColor: color,
        backgroundColor: color,
        borderWidth: isFocus ? 3 : 2,
        tension: 0.3,
        pointRadius: points.length <= 12 ? 3 : 0,
        pointHoverRadius: 5,
      };
    });
    return { labels, datasets };
  }, [history, latest, matches, mode, focus, accent]);

  if (labels.length < 2) {
    return <p className="loading">{t.noHistory}</p>;
  }

  return (
    <div className="chart-wrap">
      <Line
        data={{ labels, datasets }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          scales: {
            x: {
              ticks: { color: muted, maxRotation: 60, minRotation: 0, autoSkip: false },
              grid: { display: false },
            },
            y: {
              beginAtZero: true,
              title: { display: true, text: `${t.champion} %`, color: muted },
              ticks: { color: muted, callback: (v) => `${v}%` },
              grid: { color: gridColor },
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
