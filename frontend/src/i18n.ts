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
  // What-if panel
  whatIf: string;
  whatIfIntro: string;
  whatIfReset: string;
  whatIfSimulating: string;
  whatIfBaseline: string;
  whatIfNew: string;
  whatIfDelta: string;
  whatIfElo: string;
  whatIfPickTeams: string;
  show: string;
  hide: string;
  // Sweden deep-dive
  swedenDeepDive: string;
  swedenSurvival: string;
  swedenScenario: string;
  swedenScenarioIntro: string;
  scenarioReset: string;
  resultWin: string;
  resultDraw: string;
  resultLoss: string;
  swedenVs: string;
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
    whatIf: "Tänk om?",
    whatIfIntro:
      "Justera lagens Elo-betyg och se hur titeloddsen förändras. Simuleringen körs på servern (20 000 turneringar).",
    whatIfReset: "Återställ",
    whatIfSimulating: "Simulerar…",
    whatIfBaseline: "Nuläge",
    whatIfNew: "Nytt",
    whatIfDelta: "Skillnad",
    whatIfElo: "Elo",
    whatIfPickTeams: "Lag att justera",
    show: "Visa",
    hide: "Dölj",
    swedenDeepDive: "Sverige: djupdykning",
    swedenSurvival: "Sveriges väg, runda för runda",
    swedenScenario: "Vad måste hända?",
    swedenScenarioIntro:
      "Välj hypotetiska resultat i Sveriges tre gruppmatcher och se hur chanserna förändras.",
    scenarioReset: "Återställ scenario",
    resultWin: "Vinst",
    resultDraw: "Oavgjort",
    resultLoss: "Förlust",
    swedenVs: "Sverige mot",
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
    whatIf: "What if?",
    whatIfIntro:
      "Adjust teams' Elo ratings and see how the title odds shift. The simulation runs server-side (20,000 tournaments).",
    whatIfReset: "Reset",
    whatIfSimulating: "Simulating…",
    whatIfBaseline: "Now",
    whatIfNew: "New",
    whatIfDelta: "Delta",
    whatIfElo: "Elo",
    whatIfPickTeams: "Teams to adjust",
    show: "Show",
    hide: "Hide",
    swedenDeepDive: "Sweden: deep dive",
    swedenSurvival: "Sweden's path, round by round",
    swedenScenario: "What must happen?",
    swedenScenarioIntro:
      "Pick hypothetical results for Sweden's three group matches and see how the chances change.",
    scenarioReset: "Reset scenario",
    resultWin: "Win",
    resultDraw: "Draw",
    resultLoss: "Loss",
    swedenVs: "Sweden vs",
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
