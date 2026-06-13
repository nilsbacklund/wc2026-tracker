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

export function MatchList({ matches, mode }: Props) {
  // Show played + live + the next upcoming few, most recent activity first.
  const active = matches.filter((m) => m.status !== "scheduled" && m.home);
  const upcoming = matches
    .filter((m) => m.status === "scheduled" && m.home)
    .slice(0, 6);
  const shown = [...active, ...upcoming];

  return (
    <div>
      {shown.map((m) => (
        <div className="match" key={m.id}>
          <span>
            {flag(m.home)} {m.home} <span style={{ opacity: 0.5 }}>v</span>{" "}
            {m.away} {flag(m.away)}
          </span>
          <span style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
            {m.home_score != null && (
              <strong>
                {m.home_score}–{m.away_score}
              </strong>
            )}
            <Badge status={m.status} minute={m.minute} mode={mode} />
          </span>
        </div>
      ))}
    </div>
  );
}
