import type { Mode } from "../types";
import { STRINGS } from "../i18n";
import { flag } from "../flags";

interface Props {
  focus: string[];
  allTeams: string[];
  mode: Mode;
  onChange: (next: string[]) => void;
}

// Neutral-mode team picker: choose teams to highlight in the table/chart and
// give each its own focus panel. Chips for current picks + a dropdown to add.
export function FocusPicker({ focus, allTeams, mode, onChange }: Props) {
  const t = STRINGS[mode];
  const available = allTeams
    .filter((tm) => !focus.includes(tm))
    .sort((a, b) => a.localeCompare(b));

  return (
    <section className="panel">
      <h2>{t.focusHeading}</h2>
      <p className="subtle" style={{ marginTop: 0 }}>
        {t.focusHint}
      </p>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "0.5rem",
          alignItems: "center",
        }}
      >
        {focus.map((tm) => (
          <button
            key={tm}
            className="chip active"
            onClick={() => onChange(focus.filter((x) => x !== tm))}
            title={t.focusAdd}
          >
            <span>
              {flag(tm)} {tm}
            </span>
            <span className="x">×</span>
          </button>
        ))}
        <select
          className="chip"
          value=""
          onChange={(e) => {
            if (e.target.value) onChange([...focus, e.target.value]);
          }}
          style={{ appearance: "auto" }}
        >
          <option value="">+ {t.focusAdd}</option>
          {available.map((tm) => (
            <option key={tm} value={tm}>
              {tm}
            </option>
          ))}
        </select>
      </div>
    </section>
  );
}
