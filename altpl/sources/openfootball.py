"""Parser for the openfootball/england Football.TXT match files.

Two layouts occur in the repo:
  ``  15:00  Home Team         2-1 (1-0)  Away Team``        (older seasons)
  ``  15:00  Home Team   v Away Team         2-1 (1-0)``     (newer seasons)
Lines tagged [cancelled], [postponed] or [abandoned] carry no result and are
dropped; [awarded] results are kept and flagged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

DATE_RE = re.compile(r"^\s*(?:\[)?(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?\s+([A-Z][a-z]{2})/?\s*(\d{1,2})(?:\s+(\d{4}))?(?:\])?\s*$")
TIME = r"(?:\d{1,2}[:.]\d{2}\s+)?"
SCORE = r"(\d+)\s*-\s*(\d+)(?:\s*\([^)]*\))?(?:\s*\([^)]*\))?"
TAG = r"(?:\s*\[(?P<tag>[a-z ]+)\])?"
# layout 1: home score away
L1 = re.compile(rf"^\s+{TIME}(?P<home>\S.*?\S)\s+{SCORE}\s+(?P<away>\S.*?\S){TAG}\s*$")
# layout 2: home v away score
L2 = re.compile(rf"^\s+{TIME}(?P<home>\S.*?\S)\s+v\s+(?P<away>\S.*?\S)\s+{SCORE}{TAG}\s*$")
NORESULT = re.compile(r"\[(cancelled|postponed|abandoned)\]")


@dataclass
class Match:
    date: date | None
    home: str
    away: str
    hg: int
    ag: int
    awarded: bool
    line: int
    stage: str = "league"  # "league" or "playoff"


def parse_file(path: Path, season_start: int) -> list[Match]:
    """Parse one division file. ``season_start`` is e.g. 2008 for 2008/09."""
    out: list[Match] = []
    cur: date | None = None
    stage = "league"
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        if line.startswith("▪"):
            if re.search(r"play-?offs?|finals?|semi", line, re.I):
                stage = "playoff"
            continue
        m = DATE_RE.match(line)
        if m:
            mon, day, yr = MONTHS[m.group(1)], int(m.group(2)), m.group(3)
            year = int(yr) if yr else (season_start if mon >= 7 else season_start + 1)
            cur = date(year, mon, day)
            continue
        if NORESULT.search(line):
            continue
        m = L2.match(line)
        if m:
            home, away, hg, ag = m.group("home"), m.group("away"), m.group(3), m.group(4)
        else:
            m = L1.match(line)
            if not m:
                continue
            home, hg, ag, away = m.group("home"), m.group(2), m.group(3), m.group("away")
        out.append(Match(cur, home.strip(), away.strip(), int(hg), int(ag),
                         (m.group("tag") or "") == "awarded", n, stage))
    return out
