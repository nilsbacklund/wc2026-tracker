import type { Match, Snapshot } from "../types";
import { METRIC_ORDER, STRINGS } from "../i18n";
import { flag } from "../flags";

interface Props {
  snapshot: Snapshot;
  matches: Match[];
}

// Sweden-specific deep dive, shown only in Sverigeläge.
export function SwedenPanel({ snapshot, matches }: Props) {
  const t = STRINGS.sv;
  const p = snapshot.probs["Sweden"];
  if (!p) return null;

  const swedenMatches = matches.filter(
    (m) => m.home === "Sweden" || m.away === "Sweden",
  );

  return (
    <section className="panel" style={{ borderColor: "var(--accent)" }}>
      <h2>
        {flag("Sweden")} {t.swedenRoute}
      </h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        {METRIC_ORDER.map((m) => (
          <div
            key={m}
            style={{
              flex: "1 1 120px",
              background: "var(--panel-2)",
              borderRadius: 8,
              padding: "0.7rem 0.9rem",
            }}
          >
            <div style={{ color: "var(--muted)", fontSize: "0.72rem" }}>
              {t.metrics[m]}
            </div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>
              {p[m].toFixed(1)}%
            </div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: "1rem" }}>
        {swedenMatches.map((m) => {
          const opp = m.home === "Sweden" ? m.away : m.home;
          return (
            <div className="match" key={m.id}>
              <span>
                {flag("Sweden")} Sverige <span style={{ opacity: 0.5 }}>v</span>{" "}
                {opp} {flag(opp)}
              </span>
              <span>
                {m.home_score != null
                  ? `${m.home_score}–${m.away_score}`
                  : m.matchday
                    ? `Omgång ${m.matchday}`
                    : ""}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
