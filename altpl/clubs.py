"""Club identity: map every source spelling to one canonical club_id."""
from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

REF = Path(__file__).resolve().parent.parent / "data" / "reference"
_SUFFIX = re.compile(r"\s+(?:A\.?F\.?C\.?|F\.?C\.?)$")


@lru_cache
def _tables() -> tuple[dict[str, str], dict[str, str]]:
    lookup, names = {}, {}
    with (REF / "clubs.csv").open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            names[row["club_id"]] = row["name"]
            for alias in [row["name"], *filter(None, row["aliases"].split("|"))]:
                key = alias.casefold()
                if key in lookup and lookup[key] != row["club_id"]:
                    raise ValueError(f"alias {alias!r} is ambiguous")
                lookup[key] = row["club_id"]
    return lookup, names


def club_id(raw: str, season: int) -> str:
    """Resolve a source team name to a club_id. ``season`` is the start year.

    Chester City (expelled 2010, wound up) and the phoenix Chester FC are
    different clubs; sources call both "Chester", so the season decides.
    """
    name = raw.replace("\x92", "'").strip()
    if name.casefold() in {"chester", "chester fc"}:
        return "chester_city" if season <= 2009 else "chester"
    lookup, _ = _tables()
    for cand in (name, _SUFFIX.sub("", name)):
        if cand.casefold() in lookup:
            return lookup[cand.casefold()]
    raise KeyError(f"unknown club name {raw!r} ({season})")


def club_name(cid: str) -> str:
    return _tables()[1][cid]
