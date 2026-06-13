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
import type { Mode, Snapshot } from "../types";
import { STRINGS } from "../i18n";
import { flag } from "../flags";

ChartJS.register(LineElement, PointElement, LinearScale, TimeScale, Tooltip, Legend);

// Distinct line colors; Sweden always gets the theme yellow.
const COLORS = [
  "#5b8cff", "#f06595", "#46d39a", "#c77dff",
  "#ff9f40", "#36cfd1", "#ffd000", "#9aa7c2",
];

interface Props {
  history: Snapshot[];
  latest: Snapshot;
  mode: Mode;
}

export function RaceChart({ history, latest, mode }: Props) {
  const t = STRINGS[mode];
  // Theme-aware axis/legend colors (read once per render from CSS vars).
  const css = getComputedStyle(document.documentElement);
  const muted = css.getPropertyValue("--muted").trim() || "#9aa7c2";
  const text = css.getPropertyValue("--text").trim() || "#eef2fb";
  const gridColor = "rgba(255,255,255,0.06)";

  const data = useMemo(() => {
    const ranked = Object.keys(latest.probs).sort(
      (a, b) => latest.probs[b].champ - latest.probs[a].champ,
    );
    const picks = ranked.slice(0, 6);
    if (mode === "sv" && !picks.includes("Sweden")) picks.push("Sweden");

    return {
      datasets: picks.map((team, i) => ({
        label: `${flag(team)} ${team}`,
        data: history.map((s) => ({
          x: new Date(s.ts).getTime(),
          y: s.probs[team]?.champ ?? null,
        })),
        borderColor: team === "Sweden" ? "#ffd000" : COLORS[i % COLORS.length],
        backgroundColor: team === "Sweden" ? "#ffd000" : COLORS[i % COLORS.length],
        borderWidth: team === "Sweden" ? 3 : 2,
        tension: 0.3,
        // Always show points so a 2-3 snapshot history is still legible.
        pointRadius: history.length <= 6 ? 3 : 0,
        pointHoverRadius: 5,
      })),
    };
  }, [history, latest, mode]);

  // Need at least two snapshots for a meaningful line.
  if (history.length < 2) {
    return <p className="loading">{t.noHistory}</p>;
  }

  return (
    <div className="chart-wrap">
      <Line
        data={data}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          interaction: { mode: "nearest", intersect: false },
          scales: {
            x: {
              type: "time",
              time: { tooltipFormat: "PPp" },
              ticks: { color: muted, maxRotation: 0, autoSkipPadding: 20 },
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
            legend: {
              labels: { color: text, usePointStyle: true, boxWidth: 8 },
            },
            tooltip: {
              callbacks: {
                label: (ctx) => `${ctx.dataset.label}: ${Number(ctx.parsed.y).toFixed(1)}%`,
              },
            },
          },
        }}
      />
    </div>
  );
}
