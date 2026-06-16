"""Parse tippningar.xlsx (the family prediction pool) into a committed TS file.

Each person predicts a champion (Vinst), runner-up (Tvåa), two semifinalists
(Semi) and four quarterfinalists (Kvart). The sheet uses Swedish team names;
we map them to the engine's canonical names and validate.

    python3 scripts/parse_tippningar.py

Stdlib only (zipfile + xml) so it doesn't depend on the project venv.
Re-run whenever tippningar.xlsx changes.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "tippningar.xlsx"
OUT = ROOT / "frontend" / "src" / "tippningar.ts"

# The 48 canonical team names the engine uses.
CANONICAL = {
    "Mexico", "South Africa", "South Korea", "Czechia", "Canada", "Bosnia",
    "Qatar", "Switzerland", "Brazil", "Morocco", "Haiti", "Scotland", "USA",
    "Paraguay", "Australia", "Turkiye", "Germany", "Curacao", "Ivory Coast",
    "Ecuador", "Netherlands", "Japan", "Sweden", "Tunisia", "Belgium", "Egypt",
    "Iran", "New Zealand", "Spain", "Cape Verde", "Saudi Arabia", "Uruguay",
    "France", "Senegal", "Iraq", "Norway", "Argentina", "Algeria", "Austria",
    "Jordan", "Portugal", "DR Congo", "Uzbekistan", "Colombia", "England",
    "Croatia", "Ghana", "Panama",
}

# Swedish (and common typos) -> canonical.
SV = {
    "frankrike": "France", "tyskland": "Germany", "brasilien": "Brazil",
    "spanien": "Spain", "sverige": "Sweden", "argentina": "Argentina",
    "argenina": "Argentina", "nederländerna": "Netherlands",
    "nederländrna": "Netherlands", "holland": "Netherlands", "england": "England",
    "norge": "Norway", "mexico": "Mexico", "mexiko": "Mexico",
    "portugal": "Portugal", "schweiz": "Switzerland", "usa": "USA",
    "marocko": "Morocco", "marockо": "Morocco", "japan": "Japan",
    "belgien": "Belgium", "tunisien": "Tunisia", "australien": "Australia",
    "kanada": "Canada", "algeriet": "Algeria", "kroatien": "Croatia",
    "uruguay": "Uruguay", "colombia": "Colombia", "ecuador": "Ecuador",
    "senegal": "Senegal", "sydkorea": "South Korea", "sydafrika": "South Africa",
    "österrike": "Austria", "egypten": "Egypt", "iran": "Iran",
    "saudiarabien": "Saudi Arabia", "qatar": "Qatar", "panama": "Panama",
    "ghana": "Ghana", "tjeckien": "Czechia", "irak": "Iraq",
    "uzbekistan": "Uzbekistan", "elfenbenskusten": "Ivory Coast",
    "nya zeeland": "New Zealand", "jordanien": "Jordan",
    "kap verde": "Cape Verde", "haiti": "Haiti", "bosnien": "Bosnia",
    "paraguay": "Paraguay",
}


def canon(name):
    s = (name or "").strip()
    if not s:
        return None
    mapped = SV.get(s.lower(), s)
    if mapped not in CANONICAL:
        sys.exit(f"Unknown team {name!r} (mapped {mapped!r}) — add it to SV map")
    return mapped


def cells():
    z = zipfile.ZipFile(XLSX)
    shared = [
        "".join(t.text or "" for t in si.iter(f"{NS}t"))
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(f"{NS}si")
    ]
    grid = {}
    for c in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(f"{NS}c"):
        ref = c.attrib["r"]
        v = c.find(f"{NS}v")
        if v is None or v.text is None:
            continue
        val = shared[int(v.text)] if c.attrib.get("t") == "s" else v.text
        m = re.match(r"([A-Z]+)(\d+)", ref)
        grid[(m.group(1), int(m.group(2)))] = val
    return grid


def main():
    g = cells()
    # Person name in row 1; their picks live in the same column.
    people = [(col, g[(col, 1)]) for col in
              [chr(c) for c in range(ord("A"), ord("Z") + 1)]
              if (col, 1) in g]
    out = []
    for col, person in people:
        champ = canon(g.get((col, 2)))
        if not champ:
            continue  # no entry (e.g. an empty column)
        out.append({
            "person": person,
            "champion": champ,
            "runnerUp": canon(g.get((col, 4))),
            "semis": [t for t in (canon(g.get((col, 6))), canon(g.get((col, 7)))) if t],
            "quarters": [t for t in (canon(g.get((col, r))) for r in (9, 10, 11, 12)) if t],
        })

    body = ",\n  ".join(json.dumps(p, ensure_ascii=False) for p in out)
    OUT.write_text(
        "// AUTO-GENERATED from tippningar.xlsx by scripts/parse_tippningar.py.\n"
        "// Do not edit by hand; re-run the script if the sheet changes.\n"
        "export interface Tippning {\n"
        "  person: string;\n"
        "  champion: string;\n"
        "  runnerUp: string | null;\n"
        "  semis: string[];\n"
        "  quarters: string[];\n"
        "}\n\n"
        f"export const TIPPNINGAR: Tippning[] = [\n  {body},\n];\n"
    )
    print(f"wrote {OUT} with {len(out)} predictions")


if __name__ == "__main__":
    main()
