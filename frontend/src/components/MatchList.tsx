import type { Match, Mode } from "../types";
import { STRINGS } from "../i18n";
import { flag } from "../flags";

interface Props {
  matches: Match[];
  mode: Mode;
}

function Badge({ status, minute, mode }: { status: Match["status"]; minute: number | null; mode: Mode }) {
  const t = STRINGS[mode];
  if (status === "in_play")
    return <span className="badge live">{minute ? `${minute}'` : t.live}</span>;
  if (status === "finished") return <span className="badge finished">{t.finished}</span>;
  return <span className="badge scheduled">{t.scheduled}</span>;
}

// Short kickoff label for scheduled matches that have a known time.
function kickoff(m: Match, mode: Mode): string {
  if (m.kickoff_utc) {
    const d = new Date(m.kickoff_utc);
    if (!isNaN(d.getTime())) {
      return d.toLocaleString(mode === "sv" ? "sv-SE" : "en-GB", {
        weekday: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    }
  }
  if (m.matchday) return (mode === "sv" ? "Omgång " : "MD ") + m.matchday;
  return "";
}

export function MatchList({ matches, mode }: Props) {
  // Live + finished first (most relevant), then the next upcoming few.
  const active = matches.filter((m) => m.status !== "scheduled" && m.home);
  const upcoming = matches
    .filter((m) => m.status === "scheduled" && m.home)
    .slice(0, 8);
  const shown = [...active, ...upcoming];

  return (
    <div>
      {shown.map((m) => (
        <div className="match" key={m.id}>
          <span>
            {flag(m.home)} {m.home} <span style={{ opacity: 0.5 }}>v</span>{" "}
            {m.away} {flag(m.away)}
          </span>
          <span style={{ display: "flex", gap: "0.7rem", alignItems: "center" }}>
            {m.home_score != null ? (
              <span className="score">
                {m.home_score}–{m.away_score}
              </span>
            ) : (
              <span className="subtle">{kickoff(m, mode)}</span>
            )}
            <Badge status={m.status} minute={m.minute} mode={mode} />
          </span>
        </div>
      ))}
    </div>
  );
}
