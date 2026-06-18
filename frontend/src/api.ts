import type { Bracket, Importance, Match, Snapshot, StandingRow, TeamProbs } from "./types";

const BASE = "/api";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
}

export const fetchLatestOdds = () => get<Snapshot>("/odds/latest");

export const fetchMatches = () =>
  get<{ matches: Match[] }>("/matches").then((d) => d.matches);

export const fetchStandings = () =>
  get<{ groups: Record<string, StandingRow[]> }>("/standings").then(
    (d) => d.groups,
  );

export const fetchTeamHistory = (team: string) =>
  get<{ team: string; points: { ts: string; probs: TeamProbs | null }[] }>(
    `/odds/history?team=${encodeURIComponent(team)}`,
  );

export const fetchHistory = () =>
  get<{ snapshots: Snapshot[] }>("/odds/history").then((d) => d.snapshots);

export const fetchImportance = () => get<Importance>("/importance");

export const fetchBracket = () => get<Bracket>("/bracket");

export interface TeamInfo {
  name: string;
  group: string;
  elo: number | null;
}

export const fetchTeams = () =>
  get<{ teams: TeamInfo[] }>("/teams").then((d) => d.teams);

export interface SimRequest {
  elo_overrides?: Record<string, number>;
  n_sims?: number;
  hypotheticals?: unknown[];
}

export async function simulate(req: SimRequest): Promise<Snapshot> {
  const res = await fetch(`${BASE}/simulate`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`simulate: ${res.status}`);
  return res.json();
}
