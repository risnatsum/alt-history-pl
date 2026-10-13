"""Download pinned snapshots of each source into data/raw/ and write
standardised per-source extracts to data/sources/.

    python -m altpl.sources.fetch
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

import pandas as pd

from altpl.config import (ENGSOCCERDATA, FOOTBALLDATA_MIRROR, OPENFOOTBALL, RAW, SEASONS,
                          SOURCES)
from altpl.sources.openfootball import parse_file

OF_FILES = {1: "1-premierleague.txt", 2: "2-championship.txt", 3: "3-league1.txt",
            4: "4-league2.txt", 5: "5-nationalleague.txt"}
FD_TIERS = {"E0": 1, "E1": 2, "E2": 3, "E3": 4, "EC": 5}
FD_KEEP = ["OddHome", "OddDraw", "OddAway", "MaxHome", "MaxDraw", "MaxAway",
           "Over25", "Under25", "HandiSize", "HandiHome", "HandiAway"]


def _get(repo_sha: tuple[str, str], path: str, dest: Path) -> Path | None:
    repo, sha = repo_sha
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            dest.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    return dest


def fetch_raw() -> None:
    for s in SEASONS:
        folder = f"{s}-{str(s + 1)[2:]}"
        for fname in OF_FILES.values():
            _get(OPENFOOTBALL, f"{folder}/{fname}", RAW / "openfootball" / folder / fname)
    for f in ["england.csv", "england5.csv", "englandplayoffs.csv"]:
        _get(ENGSOCCERDATA, f"data-raw/{f}", RAW / "engsoccerdata" / f)
    # football-data.co.uk itself is read from the committed CSVs (see extract_footballdata).
    _get(FOOTBALLDATA_MIRROR, "data/Matches.csv", RAW / "footballdata" / "Matches.csv")


def season_of(d: pd.Series) -> pd.Series:
    """Season start year from match date. 2019/20 ran on into July and August
    2020 after the Covid stoppage and 2020/21 began in September 2020, so
    July and August 2020 still belong to 2019/20."""
    y = d.dt.year - (d.dt.month < 7)
    return y.where(~((d.dt.year == 2020) & d.dt.month.isin([7, 8])), 2019)


def extract() -> None:
    SOURCES.mkdir(parents=True, exist_ok=True)
    cols = ["season", "tier", "date", "home", "away", "hg", "ag"]

    rows = []
    for s in SEASONS:
        folder = f"{s}-{str(s + 1)[2:]}"
        for tier, fname in OF_FILES.items():
            p = RAW / "openfootball" / folder / fname
            if not p.exists():
                continue
            for m in parse_file(p, s):
                if m.stage == "league":
                    rows.append((s, tier, m.date, m.home, m.away, m.hg, m.ag, m.awarded))
    of = pd.DataFrame(rows, columns=cols + ["awarded"])
    of.to_csv(SOURCES / "openfootball.csv", index=False)

    esd = pd.concat([pd.read_csv(RAW / "engsoccerdata" / "england.csv", low_memory=False),
                     pd.read_csv(RAW / "engsoccerdata" / "england5.csv")])
    esd = esd[esd.Season.isin(SEASONS)].rename(columns={
        "Season": "season", "Date": "date", "visitor": "away", "hgoal": "hg", "vgoal": "ag"})
    esd[cols].sort_values(["season", "tier", "date"]).to_csv(
        SOURCES / "engsoccerdata.csv", index=False)

    po = pd.read_csv(RAW / "engsoccerdata" / "englandplayoffs.csv")
    po[po.Season.isin(SEASONS)].to_csv(SOURCES / "engsoccerdata_playoffs.csv", index=False)

    extract_footballdata().to_csv(SOURCES / "footballdata.csv", index=False)

    fd = pd.read_csv(RAW / "footballdata" / "Matches.csv", low_memory=False,
                     encoding="utf-8")
    fd = fd[fd.Division.isin(FD_TIERS)].copy()
    fd["d"] = pd.to_datetime(fd.MatchDate)
    fd["season"] = season_of(fd.d)
    fd = fd[fd.season.isin(SEASONS)]
    fd = fd.assign(tier=fd.Division.map(FD_TIERS), date=fd.MatchDate,
                   home=fd.HomeTeam.str.replace("\x92", "'"),
                   away=fd.AwayTeam.str.replace("\x92", "'"),
                   hg=fd.FTHome.astype("Int64"), ag=fd.FTAway.astype("Int64"))
    fd[cols + ["MatchTime"] + FD_KEEP].sort_values(["season", "tier", "date"]).to_csv(
        SOURCES / "footballdata_mirror.csv", index=False)


# football-data.co.uk renamed its aggregate odds columns in 2019/20.
FD_ODDS = {
    "B365H": ["B365H"], "B365D": ["B365D"], "B365A": ["B365A"],
    "PSH": ["PSH"], "PSD": ["PSD"], "PSA": ["PSA"],          # Pinnacle, from 2012/13
    "PSCH": ["PSCH"], "PSCD": ["PSCD"], "PSCA": ["PSCA"],    # Pinnacle closing
    "MaxH": ["MaxH", "BbMxH"], "MaxD": ["MaxD", "BbMxD"], "MaxA": ["MaxA", "BbMxA"],
    "AvgH": ["AvgH", "BbAvH"], "AvgD": ["AvgD", "BbAvD"], "AvgA": ["AvgA", "BbAvA"],
    "AvgO25": ["Avg>2.5", "BbAv>2.5"], "AvgU25": ["Avg<2.5", "BbAv<2.5"],
}


def extract_footballdata() -> pd.DataFrame:
    """Read the season CSVs downloaded from football-data.co.uk by Mus (committed
    under data/sources/footballdata_csv/, named <yyyy>_<Div>.csv)."""
    out = []
    for f in sorted((SOURCES / "footballdata_csv").glob("*.csv")):
        d = pd.read_csv(f, encoding="latin-1", on_bad_lines="skip")
        d.columns = [c.replace("\ufeff", "").replace("ï»¿", "") for c in d.columns]
        d = d.dropna(subset=["HomeTeam"])
        s = 2000 + int(f.stem[:2])
        res = pd.DataFrame({
            "season": s, "tier": FD_TIERS[f.stem.split("_")[1]],
            "date": pd.to_datetime(d.Date, dayfirst=True, format="mixed").dt.date,
            "home": d.HomeTeam, "away": d.AwayTeam,
            "hg": d.FTHG.astype("Int64"), "ag": d.FTAG.astype("Int64")})
        for name, alts in FD_ODDS.items():
            col = next((a for a in alts if a in d.columns), None)
            res[name] = pd.to_numeric(d[col], errors="coerce") if col else float("nan")
        out.append(res)
    return pd.concat(out).sort_values(["season", "tier", "date"])

if __name__ == "__main__":
    fetch_raw()
    extract()
