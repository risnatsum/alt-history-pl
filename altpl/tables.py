"""League tables from match results plus real-world adjustments.

Ranking: points, then goal difference, then goals scored. Seasons decided on
points per game (2019/20 League One, League Two and National League) rank on
PPG first. Any tie still unbroken after goals scored is reported so it can be
settled by an explicit rule (head-to-head etc.) rather than silently.
"""
from __future__ import annotations

import pandas as pd

from altpl.config import REFERENCE

PPG_SEASONS = {(2019, 3), (2019, 4), (2019, 5)}


def load_adjustments() -> pd.DataFrame:
    return pd.read_csv(REFERENCE / "adjustments.csv", comment="#")


def table(results: pd.DataFrame, deductions: dict[str, int] | None = None,
          ppg: bool = False) -> pd.DataFrame:
    """Build one division's table. ``results`` has home_id, away_id, hg, ag."""
    deductions = deductions or {}
    h = pd.DataFrame({"club_id": results.home_id, "gf": results.hg, "ga": results.ag})
    a = pd.DataFrame({"club_id": results.away_id, "gf": results.ag, "ga": results.hg})
    m = pd.concat([h, a])
    m["w"] = (m.gf > m.ga).astype(int)
    m["d"] = (m.gf == m.ga).astype(int)
    m["l"] = (m.gf < m.ga).astype(int)
    t = m.groupby("club_id").agg(p=("w", "size"), w=("w", "sum"), d=("d", "sum"),
                                 l=("l", "sum"), gf=("gf", "sum"), ga=("ga", "sum"))
    for club in deductions:
        if club not in t.index:
            raise KeyError(f"deduction for {club}, which has no results here")
    t["gd"] = t.gf - t.ga
    t["pts_raw"] = 3 * t.w + t.d
    t["deduction"] = pd.Series(deductions, dtype=int).reindex(t.index).fillna(0).astype(int)
    t["pts"] = t.pts_raw - t.deduction
    t["ppg"] = (t.pts / t.p).round(6)
    keys = (["ppg"] if ppg else []) + ["pts", "gd", "gf"]
    t = t.sort_values(keys + ["club_id"], ascending=[False] * len(keys) + [True])
    t["pos"] = range(1, len(t) + 1)
    t["tied"] = t.duplicated(keys, keep=False)
    return t.reset_index()


def season_table(results: pd.DataFrame, season: int, tier: int,
                 adj: pd.DataFrame | None = None) -> pd.DataFrame:
    adj = load_adjustments() if adj is None else adj
    r = results[(results.season == season) & (results.tier == tier)]
    ded = adj[(adj.season == season) & (adj.tier == tier) & (adj.type == "deduction")]
    t = table(r, dict(zip(ded.club_id, ded.points.astype(int))),
              ppg=(season, tier) in PPG_SEASONS)
    t.insert(0, "tier", tier)
    t.insert(0, "season", season)
    return t


def all_tables(results: pd.DataFrame, adj: pd.DataFrame | None = None) -> pd.DataFrame:
    adj = load_adjustments() if adj is None else adj
    keys = results[["season", "tier"]].drop_duplicates().sort_values(["season", "tier"])
    return pd.concat([season_table(results, s, t, adj) for s, t in keys.itertuples(index=False)],
                     ignore_index=True)
