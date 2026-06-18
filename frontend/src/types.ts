export interface TeamProbs {
  advance: number;
  r16: number;
  qf: number;
  top4: number;
  final: number;
  champ: number;
  third: number; // 3rd-place probability
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

export interface MatchImpactSwing {
  min: number;
  max: number;
  base: number;
}

export interface MatchImpact {
  id: number;
  home: string | null;
  away: string | null;
  group: string | null;
  kickoff_utc: string | null;
  outcomes: {
    label: string;
    prob: number;
    score: { home: number; away: number };
    home_adv: number;
    home_champ: number;
    away_adv: number;
    away_champ: number;
  }[];
  total: { champ: number; advance: number };
  teams: Record<string, { champ: MatchImpactSwing; advance: MatchImpactSwing }>;
}

export interface Importance {
  matches: MatchImpact[];
  n_sims?: number;
}

export type ImpactMetric = "advance" | "champ";

export interface Bracket {
  r32: { match: number; home: string | null; away: string | null }[];
  elo: Record<string, number>;
}
