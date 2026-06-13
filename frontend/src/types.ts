export interface TeamProbs {
  advance: number;
  r16: number;
  qf: number;
  top4: number;
  final: number;
  champ: number;
}

export type Metric = keyof TeamProbs;

export interface Snapshot {
  id: number;
  ts: string;
  trigger: string;
  match_id: number | null;
  n_sims: number;
  probs: Record<string, TeamProbs>;
}

export interface Match {
  id: number;
  stage: string;
  grp: string | null;
  matchday: number | null;
  home: string | null;
  away: string | null;
  kickoff_utc: string | null;
  status: "scheduled" | "in_play" | "finished";
  home_score: number | null;
  away_score: number | null;
  minute: number | null;
  ko_winner: string | null;
  ko_decided_by: string | null;
}

export interface StandingRow {
  rank: number;
  team: string;
  played: number;
  w: number;
  d: number;
  l: number;
  gf: number;
  ga: number;
  gd: number;
  pts: number;
}

export interface HistoryPoint {
  ts: string;
  trigger: string;
  match_id: number | null;
  probs: TeamProbs | null;
}

export type Mode = "sv" | "neutral";
