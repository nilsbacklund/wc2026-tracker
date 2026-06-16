import type { Metric, TeamProbs } from "./types";

export interface Bracket {
  champion: string;
  runnerUp: string;
  semis: string[];
  quarters: string[];
}

// The model's most-likely bracket: greedily take the most probable team at each
// stage (champion by champ%, the other finalist by final%, then the two most
// likely remaining semifinalists, then four quarterfinalists), never reusing a
// team.
export function modelBracket(probs: Record<string, TeamProbs>): Bracket {
  const byMetric = (m: Metric) =>
    Object.keys(probs).sort((a, b) => probs[b][m] - probs[a][m]);
  const used = new Set<string>();
  const take = (m: Metric, count: number) => {
    const out: string[] = [];
    for (const team of byMetric(m)) {
      if (used.has(team)) continue;
      used.add(team);
      out.push(team);
      if (out.length === count) break;
    }
    return out;
  };
  return {
    champion: take("champ", 1)[0],
    runnerUp: take("final", 1)[0],
    semis: take("top4", 2),
    quarters: take("qf", 4),
  };
}
