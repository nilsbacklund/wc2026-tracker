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

const COLORS = [
  "#ffcd00", "#4a9eff", "#ff5c5c", "#46d39a", "#c77dff",
  "#ff9f40", "#36cfd1", "#f06595",
];

interface Props {
  history: Snapshot[];
  latest: Snapshot;
  mode: Mode;
}

export function RaceChart({ history, latest, mode }: Props) {
  const t = STRINGS[mode];

  const data = useMemo(() => {
    // Top 6 by current champ%, plus Sweden in Sverigeläge.
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
        borderColor: team === "Sweden" ? "#ffcd00" : COLORS[i % COLORS.length],
        backgroundColor: "transparent",
        borderWidth: team === "Sweden" ? 3 : 2,
        tension: 0.25,
        pointRadius: history.length <= 2 ? 3 : 0,
      })),
    };
  }, [history, latest, mode]);

  if (history.length < 2) {
    return <p className="loading">{t.noHistory}</p>;
  }

  return (
    <Line
      data={data}
      options={{
        responsive: true,
        interaction: { mode: "nearest", intersect: false },
        scales: {
          x: { type: "time", ticks: { color: "#8b98a5" }, grid: { display: false } },
          y: {
            title: { display: true, text: `${t.champion} %`, color: "#8b98a5" },
            ticks: { color: "#8b98a5" },
            grid: { color: "rgba(255,255,255,0.05)" },
          },
        },
        plugins: {
          legend: { labels: { color: "#e6edf3", usePointStyle: true } },
        },
      }}
    />
  );
}
