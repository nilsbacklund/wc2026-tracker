import type { Metric, Mode } from "./types";

interface Strings {
  title: string;
  subtitle: string;
  champion: string;
  raceTitle: string;
  oddsTable: string;
  standings: string;
  matches: string;
  team: string;
  group: string;
  played: string;
  swedenPanel: string;
  swedenRoute: string;
  noHistory: string;
  live: string;
  finished: string;
  scheduled: string;
  updated: string;
  modeToggle: string;
  metrics: Record<Metric, string>;
}

export const STRINGS: Record<Mode, Strings> = {
  sv: {
    title: "VM 2026 – Liveodds",
    subtitle:
      "Monte Carlo-simulering efter varje resultat. 20 000 turneringar per uppdatering.",
    champion: "Världsmästare",
    raceTitle: "Titelodds över tid",
    oddsTable: "Oddstabell",
    standings: "Gruppställning",
    matches: "Matcher",
    team: "Lag",
    group: "Grupp",
    played: "S",
    swedenPanel: "Sverige",
    swedenRoute: "Sveriges väg genom turneringen",
    noHistory: "Historik fylls på allt eftersom matcher spelas.",
    live: "Live",
    finished: "Slut",
    scheduled: "Kommande",
    updated: "Uppdaterad",
    modeToggle: "Neutralt läge",
    metrics: {
      advance: "Vidare från grupp",
      r16: "Åttondel",
      qf: "Kvartsfinal",
      top4: "Topp 4",
      final: "Final",
      champ: "Guld",
    },
  },
  neutral: {
    title: "World Cup 2026 – Live Odds",
    subtitle:
      "Monte Carlo simulation after every result. 20,000 tournaments per update.",
    champion: "Champion",
    raceTitle: "Title odds over time",
    oddsTable: "Odds table",
    standings: "Group standings",
    matches: "Matches",
    team: "Team",
    group: "Group",
    played: "P",
    swedenPanel: "Sweden",
    swedenRoute: "Sweden's route through the tournament",
    noHistory: "History accumulates as matches are played.",
    live: "Live",
    finished: "FT",
    scheduled: "Upcoming",
    updated: "Updated",
    modeToggle: "Sverigeläge",
    metrics: {
      advance: "Advance",
      r16: "Round of 16",
      qf: "Quarterfinal",
      top4: "Top 4",
      final: "Final",
      champ: "Champion",
    },
  },
};

export const METRIC_ORDER: Metric[] = [
  "advance",
  "r16",
  "qf",
  "top4",
  "final",
  "champ",
];
