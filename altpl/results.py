"""Build the canonical results table from football-data, checked against two other sources.

Every fixture is keyed by (season, tier, home club, away club). football-data is
the source (Mus, 13 Oct 2026): its score is used whenever it has the match. The
other sources only fill matches football-data lacks and flag disagreements,
which are written to data/processed/source_conflicts.csv. An entry in
data/reference/result_overrides.csv beats everything.
"""
from __future__ import annotations

import pandas as pd

from altpl.clubs import club_id
from altpl.config import PROCESSED, REFERENCE, SOURCES

# The GitHub mirror of football-data.co.uk (footballdata_mirror.csv) is a copy of
# football-data, so it stands in for 2013/14 PL, the one file missing from Mus's
# download, and is otherwise unused.
SOURCE_PRIORITY = ["footballdata", "engsoccerdata", "openfootball"]
MIRROR_GAPS = {(2013, 1)}
KEY = ["season", "tier", "home_id", "away_id"]


def load_source(name: str) -> pd.DataFrame:
    d = pd.read_csv(SOURCES / f"{name}.csv", low_memory=False)
    d = d.dropna(subset=["hg", "ag"])
    d["home_id"] = [club_id(n, s) for n, s in zip(d.home, d.season)]
    d["away_id"] = [club_id(n, s) for n, s in zip(d.away, d.season)]
    d["source"] = name
    return d


def expunged() -> pd.DataFrame:
    adj = pd.read_csv(REFERENCE / "adjustments.csv", comment="#")
    return adj[adj.type == "expunged"][["season", "tier", "club_id"]]


def build() -> tuple[pd.DataFrame, pd.DataFrame]:
    srcs = {n: load_source(n) for n in SOURCE_PRIORITY}
    mirror = load_source("footballdata_mirror")
    mirror = mirror[[(a, b) in MIRROR_GAPS for a, b in zip(mirror.season, mirror.tier)]]
    srcs["footballdata"] = pd.concat([srcs["footballdata"], mirror.assign(source="footballdata")],
                                     ignore_index=True)
    long = pd.concat(srcs.values(), ignore_index=True)
    long["hg"] = long.hg.astype(int)
    long["ag"] = long.ag.astype(int)

    # Drop matches of clubs whose record was expunged (some sources keep them).
    ex = expunged()
    drop = pd.Series(False, index=long.index)
    for r in ex.itertuples():
        drop |= (long.season == r.season) & (long.tier == r.tier) & (
            (long.home_id == r.club_id) | (long.away_id == r.club_id))
    long = long[~drop]

    overrides = pd.read_csv(REFERENCE / "result_overrides.csv", comment="#")
    ov = {(r.season, r.tier, r.home_id, r.away_id): (r.hg, r.ag, r.reason)
          for r in overrides.itertuples()}

    rows, conflicts = [], []
    for key, g in long.groupby(KEY, sort=False):
        scores = g.groupby(["hg", "ag"]).source.apply(list)
        n_src = len(g)
        if key in ov:
            hg, ag, why = ov[key]
            basis = f"override: {why}"
        elif len(scores) == 1:
            (hg, ag), = scores.index
            basis = "agree" if n_src > 1 else f"single:{g.source.iloc[0]}"
        else:
            best = min(g.itertuples(), key=lambda r: SOURCE_PRIORITY.index(r.source))
            hg, ag = best.hg, best.ag
            basis = f"split:use {best.source}"
        if len(scores) > 1:
            conflicts.append({**dict(zip(KEY, key)), "chosen": f"{hg}-{ag}", "basis": basis,
                              **{s: f"{a}-{b}" for (a, b), ss in scores.items() for s in ss}})
        first = g.sort_values("source", key=lambda s: s.map(SOURCE_PRIORITY.index)).iloc[0]
        awarded = bool(g.get("awarded", pd.Series(dtype=bool)).fillna(False).astype(bool).any())
        rows.append({**dict(zip(KEY, key)), "date": first.date, "hg": int(hg), "ag": int(ag),
                     "awarded": awarded, "n_sources": n_src, "basis": basis})
    res = pd.DataFrame(rows).sort_values(["season", "tier", "date", "home_id"])
    return res.reset_index(drop=True), pd.DataFrame(conflicts)


if __name__ == "__main__":
    PROCESSED.mkdir(parents=True, exist_ok=True)
    res, conf = build()
    res.to_csv(PROCESSED / "results.csv", index=False)
    conf.to_csv(PROCESSED / "source_conflicts.csv", index=False)
    print(len(res), "results;", len(conf), "conflicts")
