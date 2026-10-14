"""Standard outputs of a simulation (project spec, "Standard outputs"), as tables.

Every number here is a model estimate from the Monte Carlo runs, not a fact; the
real columns are the facts they are compared with.

- ``expected_tables``: each club's average points and position in each division and
  season, with 5th-95th percentile ranges and its chances of the title, promotion,
  the play-offs and relegation, next to the real table.
- ``whos_where``: the chance of each club being in each division each season.
- ``champions``: the real champion of each division against each club's chance of
  winning it in the simulation.
- ``compare_variants``: the same club-season measures for several variants side by side.
- ``write_workbook``: all of the above in one spreadsheet.

European places depend on each season's UEFA allocation and the cup winners; they
are not in the engine yet (E4 needs them for UEFA money), so the PL tables give
top-4 to top-7 chances instead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from altpl.clubs import club_name
from altpl.config import season_label
from altpl.simulator import AUTO, PLAYOFF, RELEGATED, TIERS, Reality, Simulation

DIV = {1: "Premier League", 2: "Championship", 3: "League One", 4: "League Two",
       5: "National League"}


def expected_tables(sim: Simulation, reality: Reality) -> pd.DataFrame:
    rows = []
    real = reality.tables.set_index(["season", "club_id"])
    for j, s in enumerate(sim.seasons):
        tier, pos, pts, oc = sim.tier[:, j], sim.pos[:, j], sim.pts[:, j], sim.outcome[:, j]
        for k in TIERS:
            rule = sim.world.rules.loc[(s, k)]
            inn = tier == k
            p_in = inn.mean(0)
            cl = np.flatnonzero(p_in > 0)
            if not len(cl):
                continue
            ptsf = np.where(inn, pts, np.nan)[:, cl]
            posf = np.where(inn, pos, np.nan)[:, cl]
            ink = inn[:, cl]
            ock = oc[:, cl]
            posk = pos[:, cl]
            d = pd.DataFrame({
                "season": s, "season_label": season_label(s), "tier": k, "division": DIV[k],
                "club_id": [sim.clubs[c] for c in cl],
                "club": [club_name(sim.clubs[c]) for c in cl],
                "p_in_division": p_in[cl],
                "xpts": np.nanmean(ptsf, 0),
                "pts_p05": np.nanpercentile(ptsf, 5, axis=0),
                "pts_p95": np.nanpercentile(ptsf, 95, axis=0),
                "xpos": np.nanmean(posf, 0),
                "pos_p05": np.nanpercentile(posf, 5, axis=0),
                "pos_p95": np.nanpercentile(posf, 95, axis=0),
                "p_title": (ink & (posk == 1)).mean(0),
            })
            if k == 1:
                for top in (4, 5, 6, 7):
                    d[f"p_top{top}"] = (ink & (posk <= top)).mean(0)
            else:
                d["p_auto_promotion"] = (ink & (ock == AUTO)).mean(0)
                d["p_playoffs"] = (ink & (posk >= rule.playoff_from) & (posk <= rule.playoff_to)).mean(0) \
                    if rule.playoff_up else 0.0
                d["p_promoted"] = (ink & np.isin(ock, (AUTO, PLAYOFF))).mean(0)
            d["p_relegated"] = (ink & (ock == RELEGATED)).mean(0)
            r = [real.loc[(s, sim.clubs[c])] if (s, sim.clubs[c]) in real.index else None for c in cl]
            d["real_tier"] = [x.tier if x is not None else np.nan for x in r]
            same = d.real_tier == k
            d["real_pts"] = [x.pts if x is not None else np.nan for x in r]
            d["real_pos"] = [x.pos if x is not None else np.nan for x in r]
            d.loc[~same, ["real_pts", "real_pos"]] = np.nan
            d["real_outcome"] = [x.outcome if x is not None and isinstance(x.outcome, str) else ""
                                 for x in r]
            d.loc[~same, "real_outcome"] = ""
            d["pts_vs_real"] = d.xpts - d.real_pts
            d["pos_vs_real"] = d.xpos - d.real_pos
            # clubs usually in the division first, in expected order; rare visitors after
            d = d.assign(_rare=d.p_in_division < 0.5).sort_values(["_rare", "xpos", "club_id"])
            rows.append(d.drop(columns="_rare"))
    return pd.concat(rows, ignore_index=True)


def whos_where(sim: Simulation) -> pd.DataFrame:
    """Chance of each club being in each division each season (columns
    p_tier1..p_tier5 and p_out, outside the modelled pyramid). Includes the season
    after the last simulated one when the run carried its moves into it."""
    seasons = sim.seasons + ([sim.seasons[-1] + 1] if sim.tier[:, -1].any() else [])
    rows = []
    for j, s in enumerate(seasons):
        t = sim.tier[:, j]
        seen = np.flatnonzero((t > 0).any(0))
        d = pd.DataFrame({"season": s, "season_label": season_label(s),
                          "club_id": [sim.clubs[c] for c in seen],
                          "club": [club_name(sim.clubs[c]) for c in seen]})
        for k in TIERS:
            d[f"p_tier{k}"] = (t[:, seen] == k).mean(0)
        d["p_out"] = (t[:, seen] == 0).mean(0)
        d["expected_tier"] = sum(k * d[f"p_tier{k}"] for k in TIERS) / (1 - d.p_out).clip(1e-9)
        rows.append(d)
    return pd.concat(rows, ignore_index=True)


def whos_where_grid(sim: Simulation, tier: int = 1) -> pd.DataFrame:
    """Club x season grid of the chance of being in ``tier``."""
    w = whos_where(sim)
    g = w.pivot_table(index="club", columns="season_label", values=f"p_tier{tier}", fill_value=0.0)
    return g[(g > 0).any(axis=1)].sort_values(list(g.columns), ascending=False)


def champions(sim: Simulation, reality: Reality, top: int = 3) -> pd.DataFrame:
    real = reality.tables[reality.tables.pos == 1].set_index(["season", "tier"]).club_id
    rows = []
    for j, s in enumerate(sim.seasons):
        for k in TIERS:
            win = (sim.tier[:, j] == k) & (sim.pos[:, j] == 1)
            p = win.mean(0)
            best = np.argsort(-p)[:top]
            rc = real.get((s, k))
            rows.append({
                "season": s, "season_label": season_label(s), "tier": k, "division": DIV[k],
                "real_champion": club_name(rc) if rc else "",
                "p_real_champion": p[reality.ci[rc]] if rc else np.nan,
                **{f"sim_{i + 1}": f"{club_name(sim.clubs[c])} ({p[c]:.1%})"
                   for i, c in enumerate(best) if p[c] > 0},
            })
    return pd.DataFrame(rows)


def compare_variants(sims: dict, reality: Reality) -> pd.DataFrame:
    """One row per club-season: chance of each division, average points and
    position, for every variant side by side."""
    out = None
    for name, sim in sims.items():
        w = whos_where(sim)[["season", "club_id", "club", "p_tier1", "p_tier2", "p_tier3",
                             "p_tier4", "p_tier5", "p_out"]]
        e = expected_tables(sim, reality)
        # points and position in the club's most likely division
        e = e.sort_values("p_in_division", ascending=False).drop_duplicates(["season", "club_id"])
        e = e[["season", "club_id", "division", "xpts", "xpos", "p_promoted", "p_relegated"]] \
            if "p_promoted" in e else e[["season", "club_id", "division", "xpts", "xpos"]]
        w = w.merge(e, on=["season", "club_id"], how="left")
        w = w.set_index(["season", "club_id", "club"])
        w.columns = pd.MultiIndex.from_product([[name], w.columns])
        out = w if out is None else out.join(w, how="outer")
    return out.reset_index()


def write_workbook(sim: Simulation, reality: Reality, path, extra: dict | None = None) -> None:
    """Every standard table of one simulation in a spreadsheet."""
    with pd.ExcelWriter(path) as xw:
        about = pd.DataFrame({"item": ["world", "seasons", "runs", "seed", "real results kept",
                                       "step-up penalty", "money boost", "note"],
                              "value": [sim.world.name,
                                        f"{season_label(sim.seasons[0])} to {season_label(sim.seasons[-1])}",
                                        sim.runs, sim.seed, sim.anchored, sim.world.step_up,
                                        sim.world.money_boost,
                                        "Simulated numbers are model estimates, not facts."]})
        about.to_excel(xw, sheet_name="about", index=False)
        expected_tables(sim, reality).to_excel(xw, sheet_name="expected_tables", index=False)
        whos_where(sim).to_excel(xw, sheet_name="whos_where", index=False)
        whos_where_grid(sim, 1).to_excel(xw, sheet_name="pl_membership_grid")
        champions(sim, reality).to_excel(xw, sheet_name="champions", index=False)
        for name, df in (extra or {}).items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
