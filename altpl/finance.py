"""Stage E4 finance model: what a scenario does to each club's revenue.

For every run, season and club the model prices where the club played and finished,
then subtracts what the same model gives for where the club really played and
finished. Errors in the model's revenue *levels* cancel in that difference; what
matters is how revenue changes with division and position.

Revenue components (all sourced in ``data/reference/finance``; see the assumptions
log, E4 entries, and ``docs/e4_validation.md``):

- ``pl_central``: Premier League central payments by league position: equal share,
  overseas TV and central commercial (equal shares), merit payment per place, and
  facility fees (TV appearances; fitted as a straight line in position, because who
  gets picked for TV is about the club as much as the position).
- ``parachute``: parachute payments to clubs relegated from the PL, under the rules
  of the season they went down (number of years depends on how long they had been
  in the PL), paid while they are outside the PL.
- ``solidarity``: PL solidarity payments to EFL clubs (Championship clubs only when
  not on a parachute) and to the National League where sourced.
- ``efl_central``: the EFL's own central distribution per club, by division.
- ``uefa``: UEFA prize money for a European place earned through the PL table,
  paid in the following season; the allocation by league position is the one that
  really happened each season (cup winners' routes are taken as real and so cancel).
- ``matchday_commercial``: matchday and commercial revenue gained per division
  climbed, estimated from clubs' accounts around promotion and relegation.

Amounts are nominal pounds of the season paid; ``real_gbp`` restates them in
2025/26 pounds with the ONS CPI. Every number this module produces is a model
estimate, not a fact.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from altpl.clubs import club_name
from altpl.config import FIRST_SEASON, PROCESSED, SOURCES, season_label
from altpl.simulator import Reality, Simulation

COMPONENTS = ("pl_central", "parachute", "solidarity", "efl_central", "uefa",
              "matchday_commercial")
PRE = 8          # seasons of PL history before 2008/09 kept for parachutes
BASE_SEASON = 2025   # 2025/26 pounds
NOT_PL = 9           # tier code for "a club outside the PL" in the pre-2008 history


# ---------------------------------------------------------------- price list


class Prices:
    """The price list (``data/processed/finance_prices.csv``, built by
    ``altpl.finance_data``): what each division, position and status is worth in each
    season. ``overrides`` {(season, item): value} replaces single prices, e.g. for a
    sensitivity."""

    def __init__(self, overrides: dict | None = None):
        p = pd.read_csv(PROCESSED / "finance_prices.csv")
        self.table = p
        self.v = {(int(s), i): float(x) for s, i, x in zip(p.season, p["item"], p.value)}
        self.v.update(overrides or {})
        self.para_rules = pd.read_csv(PROCESSED / "finance_parachute_rules.csv")
        self.places = pd.read_csv(PROCESSED / "finance_uefa_places.csv")
        self.uplift = pd.read_csv(PROCESSED / "finance_uplift.csv")

    def get(self, season, item, default=0.0):
        return self.v.get((season, item), default)

    def pl_central(self, season: int, pos: np.ndarray) -> np.ndarray:
        """Central payment for finishing ``pos`` in the PL of ``season``: the average
        club's payment less its average merit, plus merit for the place (one unit per
        place above 21st, none below) and the facility-fee slope around mid-table."""
        base = self.get(season, "pl_base")
        unit = self.get(season, "pl_merit_unit")
        slope = self.get(season, "pl_fac_slope")
        merit = unit * np.maximum(21 - pos, 0)
        return base + merit + slope * (pos - 10.5)

    def parachute_years(self, relegated: int, spell: np.ndarray) -> np.ndarray:
        """Years of parachute for a club relegated at the end of season ``relegated``
        after ``spell`` consecutive PL seasons."""
        r = self.para_rules
        r = r[(r.first_relegation <= relegated) & (r.last_relegation >= relegated)]
        out = np.zeros(spell.shape, np.int8)
        for row in r.itertuples():
            out[(spell >= row.min_spell) & (spell <= row.max_spell)] = row.years
        return out

    def parachute(self, season: int, year: np.ndarray) -> np.ndarray:
        lut = np.array([0.0] + [self.get(season, f"parachute_y{y}") for y in range(1, 8)])
        return lut[np.clip(year, 0, 7)]

    def solidarity_lut(self, season):
        lut = np.zeros(10)
        for t in (2, 3, 4):
            lut[t] = self.get(season, f"solidarity_t{t}")
        return lut

    def efl_lut(self, season):
        lut = np.zeros(10)
        for t in (2, 3, 4):
            lut[t] = self.get(season, f"efl_t{t}")
        return lut

    def uefa_lut(self, league_season: int) -> np.ndarray:
        """Expected UEFA prize money (pounds, paid next season) for each PL position."""
        lut = np.zeros(41)
        pl = self.places[self.places.season == league_season]
        for r in pl.itertuples():
            lut[int(r.position)] = self.get(league_season + 1, f"uefa_{r.competition}")
        return lut

    def uplift_lut(self, season):
        """Matchday and commercial revenue of each division above the National
        League's, adding up the per-step gains."""
        u = self.uplift[self.uplift.season == season].set_index("tier").step_gain
        lut = np.zeros(10)
        for t in (4, 3, 2, 1):
            lut[t] = lut[t + 1] + u.get(t, 0.0)
        return lut

    def cpi_factor(self, season: int) -> float:
        return self.get(BASE_SEASON, "cpi") / self.get(season, "cpi")


# ---------------------------------------------------------------- revenue of a history


def _pl_history(reality: Reality) -> np.ndarray:
    """PL membership (1 or NOT_PL) of every club in the PRE seasons before 2008/09."""
    pre = pd.read_csv(SOURCES / "pl_membership_pre2008.csv")
    h = np.full((PRE, len(reality.clubs)), NOT_PL, np.int8)
    for s, c in pre[["season", "club_id"]].itertuples(index=False):
        j = s - (FIRST_SEASON - PRE)
        if 0 <= j < PRE and c in reality.ci:
            h[j, reality.ci[c]] = 1
    return h


def revenue(prices: Prices, seasons: list, tier: np.ndarray, pos: np.ndarray,
            before: np.ndarray, before_pos1: np.ndarray):
    """Revenue by component for ``runs x seasons x clubs`` histories.

    ``tier``/``pos``: runs x S x C for the priced seasons. ``before``: runs x B x C
    divisions in the seasons before (real history), used for parachutes;
    ``before_pos1``: runs x C PL positions in the season just before (for UEFA money
    earned then and paid in the first priced season; 0 = not in the PL).
    Yields (season index, {component: runs x C array}).
    """
    runs, S, C = tier.shape
    B = before.shape[1]
    # parachute state carried through the seasons: years left and which year it is
    spell = np.zeros((runs, C), np.int16)       # consecutive PL seasons up to now
    left = np.zeros((runs, C), np.int8)         # parachute years still to come
    year = np.zeros((runs, C), np.int8)         # parachute year being paid
    first = seasons[0] - B   # season of before[:, 0]

    def step(prev_tier, cur_tier, s_prev):
        nonlocal spell, left, year
        was = prev_tier == 1
        now = cur_tier == 1
        down = was & ~now
        if down.any():
            yrs = prices.parachute_years(s_prev, spell)
            left = np.where(down, yrs, left)
            year = np.where(down, 0, year)
        spell = np.where(now, np.where(was, spell + 1, 1), 0)
        paying = ~now & (left > 0)
        year = np.where(paying, year + 1, 0)
        left = np.where(paying, left - 1, np.where(now, 0, left))
        return paying

    hist = np.concatenate([before, tier], axis=1)
    for j in range(1, B):
        step(hist[:, j - 1], hist[:, j], first + j - 1)
    prev_pos = before_pos1
    for j, s in enumerate(seasons):
        cur, p = tier[:, j], pos[:, j]
        prev = hist[:, B + j - 1]
        paying = step(prev, cur, s - 1)
        out = {}
        pl = cur == 1
        out["pl_central"] = np.where(pl, prices.pl_central(s, np.where(pl, p, 1)), 0.0)
        out["parachute"] = np.where(paying, prices.parachute(s, year), 0.0)
        sol = prices.solidarity_lut(s)[cur.astype(int)]
        out["solidarity"] = np.where((cur == 2) & paying, 0.0, sol) * (cur > 1)
        out["efl_central"] = prices.efl_lut(s)[cur.astype(int)] * (cur > 1) * (cur < 5)
        out["uefa"] = prices.uefa_lut(s - 1)[np.clip(prev_pos, 0, 40)] if s - 1 >= FIRST_SEASON \
            else np.zeros((runs, C))
        up = prices.uplift_lut(s)
        out["matchday_commercial"] = np.where(cur > 0, up[cur.astype(int)], 0.0)
        yield j, out
        prev_pos = np.where(pl, p, 0)


# ---------------------------------------------------------------- scenario vs reality


@dataclass
class FinanceResult:
    club_season: pd.DataFrame     # per club and season: difference vs reality, by component
    club_total: pd.DataFrame      # per club: total difference over all seasons (headline)
    real_revenue: pd.DataFrame    # the model's revenue for reality, by club-season and component


def _history_inputs(reality: Reality, sim_seasons: list, runs: int):
    """Real divisions before the first priced season (with the pre-2008 PL
    history) and real PL positions in the season just before."""
    h_pre = _pl_history(reality)
    s0 = sim_seasons[0]
    real_before = reality.tier[: s0 - FIRST_SEASON]
    before = np.concatenate([h_pre, np.where(real_before == 0, NOT_PL, real_before)], axis=0)
    pos1 = np.zeros(len(reality.clubs), np.int16)
    if s0 > FIRST_SEASON:
        t = reality.tables[(reality.tables.season == s0 - 1) & (reality.tables.tier == 1)]
        pos1[t.club_id.map(reality.ci).values] = t.pos.values
    return (np.broadcast_to(before[None], (runs,) + before.shape),
            np.broadcast_to(pos1[None], (runs, len(pos1))))


def real_arrays(reality: Reality, seasons: list):
    S, C = len(seasons), len(reality.clubs)
    tier = reality.tier[[s - FIRST_SEASON for s in seasons]][None].astype(np.int8)
    pos = np.zeros((1, S, C), np.int16)
    t = reality.tables
    for j, s in enumerate(seasons):
        g = t[t.season == s]
        pos[0, j, g.club_id.map(reality.ci).values] = g.pos.values
    return tier, pos


def finance(sim: Simulation, reality: Reality, prices: Prices | None = None,
            min_share: float = 0.05) -> FinanceResult:
    """Revenue difference between each run of ``sim`` and reality, per club and
    season and in total, by component, in nominal and 2025/26 pounds.

    ``min_share``: a club-season counts as affected when the club's division or
    position differs from reality in at least this share of runs.
    """
    P = prices or Prices()
    seasons = sim.seasons
    runs, S, C = sim.pos.shape
    tier = sim.tier[:, :S]
    rt, rp = real_arrays(reality, seasons)
    before, pos1 = _history_inputs(reality, seasons, runs)
    rb, rp1 = _history_inputs(reality, seasons, 1)
    real = {j: o for j, o in revenue(P, seasons, rt, rp, rb, rp1)}

    tot_nom = {k: np.zeros((runs, C)) for k in COMPONENTS}
    tot_real = np.zeros((runs, C))
    rows, real_rows = [], []
    names = [club_name(c) for c in sim.clubs]
    for j, out in revenue(P, seasons, tier, sim.pos, before, pos1):
        s = seasons[j]
        f = P.cpi_factor(s)
        d_all = np.zeros((runs, C))
        comp = {}
        for k in COMPONENTS:
            d = out[k] - real[j][k]
            tot_nom[k] += d
            d_all += d
            comp[k] = d.mean(0)
        tot_real += d_all * f
        differs = (tier[:, j] != rt[0, j]) | (sim.pos[:, j] != rp[0, j])
        p_div = (tier[:, j] != rt[0, j]).mean(0)
        p_diff = differs.mean(0)
        seen = np.flatnonzero((p_diff > 0) | (np.abs(d_all).max(0) > 0))
        p5, p95 = np.percentile(d_all[:, seen], [5, 95], axis=0)
        rows.append(pd.DataFrame({
            "season": s, "season_label": season_label(s), "club_id": [sim.clubs[c] for c in seen],
            "club": [names[c] for c in seen], "real_tier": rt[0, j, seen],
            "p_division_differs": p_div[seen], "p_division_or_position_differs": p_diff[seen],
            "affected": p_diff[seen] >= min_share,
            "diff_mean": d_all[:, seen].mean(0), "diff_p05": p5, "diff_p95": p95,
            **{f"diff_{k}": comp[k][seen] for k in COMPONENTS},
            "diff_mean_2025gbp": d_all[:, seen].mean(0) * f, "cpi_factor": f}))
        inn = np.flatnonzero(rt[0, j] > 0)
        real_rows.append(pd.DataFrame({
            "season": s, "club_id": [sim.clubs[c] for c in inn], "tier": rt[0, j, inn],
            "pos": rp[0, j, inn], **{k: real[j][k][0, inn] for k in COMPONENTS}}))
    cs = pd.concat(rows, ignore_index=True)
    total = sum(tot_nom.values())
    hit = cs[cs.affected].club_id.unique()
    idx = np.array([reality.ci[c] for c in hit], int)
    ct = pd.DataFrame({
        "club_id": hit, "club": [names[c] for c in idx],
        "affected_seasons": cs[cs.affected].groupby("club_id").size().reindex(hit).values,
        "total_mean": total[:, idx].mean(0),
        "total_p05": np.percentile(total[:, idx], 5, axis=0),
        "total_p95": np.percentile(total[:, idx], 95, axis=0),
        "total_mean_2025gbp": tot_real[:, idx].mean(0),
        "total_p05_2025gbp": np.percentile(tot_real[:, idx], 5, axis=0),
        "total_p95_2025gbp": np.percentile(tot_real[:, idx], 95, axis=0),
        **{f"total_{k}": tot_nom[k][:, idx].mean(0) for k in COMPONENTS},
    }).sort_values("total_mean_2025gbp", ascending=False, ignore_index=True)
    rr = pd.concat(real_rows, ignore_index=True)
    rr["total"] = rr[list(COMPONENTS)].sum(axis=1)
    return FinanceResult(cs, ct, rr)


def headline(fr: FinanceResult, n: int = 20) -> pd.DataFrame:
    """Clubs ranked by expected total gain or loss (2025/26 pounds, £m)."""
    t = fr.club_total
    t = pd.concat([t.head(n), t.tail(n)]).drop_duplicates("club_id")
    out = t[["club", "affected_seasons", "total_mean_2025gbp", "total_p05_2025gbp",
             "total_p95_2025gbp", "total_mean"]].copy()
    for c in out.columns[2:]:
        out[c] = out[c] / 1e6
    return out.rename(columns={"total_mean_2025gbp": "gain_gbp_m_2025", "total_p05_2025gbp": "p05",
                               "total_p95_2025gbp": "p95", "total_mean": "gain_gbp_m_nominal"})


def write_sheets(fr: FinanceResult) -> dict:
    """Finance tables for ``outputs.write_workbook(..., extra=...)``."""
    return {"finance_headline": headline(fr, 1000), "finance_club_total": fr.club_total,
            "finance_club_season": fr.club_season}
