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
  noHistory: string;
  live: string;
  finished: string;
  scheduled: string;
  updated: string;
  modeToggle: string;
  light: string;
  dark: string;
  metrics: Record<Metric, string>;
  // What-if panel
  whatIf: string;
  whatIfIntro: string;
  whatIfReset: string;
  whatIfSimulating: string;
  whatIfBaseline: string;
  whatIfDelta: string;
  whatIfElo: string;
  whatIfPickTeams: string;
  show: string;
  hide: string;
  // Focus / team deep-dive (generic — works for any team)
  focusHeading: string;
  focusAdd: string;
  focusHint: string;
  routeSuffix: string;
  roundByRound: string;
  fixtures: string;
  scenario: string;
  scenarioIntro: string;
  scenarioReset: string;
  resultWin: string;
  resultDraw: string;
  resultLoss: string;
  vs: string;
}

export const STRINGS: Record<Mode, Strings> = {
  sv: {
    title: "VM 2026 – Liveodds",
    subtitle:
      "Monte Carlo-simulering efter varje resultat. 20 000 turneringar per uppdatering.",
    champion: "Världsmästare",
    raceTitle: "Titelodds över matcherna",
    oddsTable: "Oddstabell",
    standings: "Gruppställning",
    matches: "Matcher",
    team: "Lag",
    group: "Grupp",
    played: "S",
    noHistory: "Historik fylls på allt eftersom matcher spelas.",
    live: "Live",
    finished: "Slut",
    scheduled: "Kommande",
    updated: "Uppdaterad",
    modeToggle: "Neutralt läge",
    light: "Ljust",
    dark: "Mörkt",
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
    whatIfDelta: "Skillnad",
    whatIfElo: "Elo",
    whatIfPickTeams: "Lag att justera",
    show: "Visa",
    hide: "Dölj",
    focusHeading: "Fokuslag",
    focusAdd: "Lägg till lag",
    focusHint:
      "Välj lag att markera i tabellen och grafen – varje lag får också en egen panel.",
    routeSuffix: "vägen genom turneringen",
    roundByRound: "Runda för runda",
    fixtures: "Gruppspelsmatcher",
    scenario: "Vad måste hända?",
    scenarioIntro:
      "Välj hypotetiska resultat i gruppmatcherna och se hur chanserna förändras.",
    scenarioReset: "Återställ scenario",
    resultWin: "Vinst",
    resultDraw: "Oavgjort",
    resultLoss: "Förlust",
    vs: "mot",
  },
  neutral: {
    title: "World Cup 2026 – Live Odds",
    subtitle:
      "Monte Carlo simulation after every result. 20,000 tournaments per update.",
    champion: "Champion",
    raceTitle: "Title odds over the matches",
    oddsTable: "Odds table",
    standings: "Group standings",
    matches: "Matches",
    team: "Team",
    group: "Group",
    played: "P",
    noHistory: "History accumulates as matches are played.",
    live: "Live",
    finished: "FT",
    scheduled: "Upcoming",
    updated: "Updated",
    modeToggle: "Sverigeläge",
    light: "Light",
    dark: "Dark",
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
    whatIfDelta: "Delta",
    whatIfElo: "Elo",
    whatIfPickTeams: "Teams to adjust",
    show: "Show",
    hide: "Hide",
    focusHeading: "Focus teams",
    focusAdd: "Add a team",
    focusHint:
      "Pick teams to highlight in the table and chart — each also gets its own panel.",
    routeSuffix: "route through the tournament",
    roundByRound: "Round by round",
    fixtures: "Group-stage matches",
    scenario: "What must happen?",
    scenarioIntro:
      "Pick hypothetical results for the group matches and see how the chances change.",
    scenarioReset: "Reset scenario",
    resultWin: "Win",
    resultDraw: "Draw",
    resultLoss: "Loss",
    vs: "vs",
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

// Display name for a team in the given mode (Sweden localizes in Sverigeläge).
export function displayName(team: string, mode: Mode): string {
  if (mode === "sv" && team === "Sweden") return "Sverige";
  return team;
}
