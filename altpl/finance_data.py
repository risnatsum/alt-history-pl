"""Stage E4 price list: turn the sourced finance tables into one value per season and item.

    python -m altpl.finance_data      # writes data/processed/finance_prices.csv

Inputs are in ``data/reference/finance/sources`` (every row carries the URL it was
read from; nothing was typed from memory). Where a season has no sourced value, a
stated fill rule supplies one and the row is marked ``filled``, so every number in
the price list says how much to trust it:

- ``sourced``: read from a cited page (possibly a secondary reproduction of an
  official table).
- ``derived``: arithmetic on sourced numbers (a sum, a difference, a share).
- ``estimate``: a cited source's own estimate (e.g. a journalist's projection before
  the official release).
- ``filled``: no source found; value from the fill rule given in ``basis``.

Amounts are pounds per club for the season paid (season = start year).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from altpl.config import LAST_SEASON, PROCESSED, REFERENCE

SRC = REFERENCE / "finance" / "sources"
SEASONS = list(range(2008, LAST_SEASON + 1))


def _row(season, item, value, status, basis, source=""):
    return dict(season=season, item=item, value=float(value), status=status, basis=basis,
                source=source)


def _fill(rows, item, seasons=SEASONS, how="interpolate"):
    """Fill seasons missing for ``item``: linear interpolation between the nearest
    seasons that have a value, or the nearest season's value at either end."""
    have = {r["season"]: r["value"] for r in rows if r["item"] == item}
    if not have:
        return
    xs = sorted(have)
    for s in seasons:
        if s in have:
            continue
        lo = [x for x in xs if x < s]
        hi = [x for x in xs if x > s]
        if lo and hi and how == "interpolate":
            a, b = lo[-1], hi[0]
            v = have[a] + (have[b] - have[a]) * (s - a) / (b - a)
            basis = f"interpolated between {a} and {b}"
        else:
            n = lo[-1] if lo else hi[0]
            v, basis = have[n], f"carried from {n}"
        rows.append(_row(s, item, v, "filled", basis))


# ---------------------------------------------------------------- PL central payments


def pl_central(rows):
    """Per season: ``pl_base`` (what every club gets bar merit and the facility-fee
    slope), ``pl_merit_unit`` (one league place's merit payment) and ``pl_fac_slope``
    (change in facility fees per place, fitted on the clubs' real fees).
    Payment for position p of 20 = base + unit * (21 - p) - unit * 10.5 ... folded into
    base: base is the average club's payment less its average merit."""
    d = pd.read_csv(SRC / "pl_payments.csv")
    for s, g in d.groupby("season"):
        g = g.sort_values("position")
        src = g.source_url.mode().iloc[0]
        unit = float(np.median(-np.diff(g.merit.values)))
        q = "estimate" if s in (2019, 2025) else "derived"
        rows.append(_row(s, "pl_merit_unit", unit, q, "median step between merit payments of "
                         "consecutive places (from 2019/20 includes the overseas merit element)", src))
        full = g.total.notna().all()
        nm = (g.total - g.merit).dropna()
        base_basis = ("mean of total minus merit over all 20 clubs" if full else
                      f"mean of total minus merit over the {len(nm)} clubs with a sourced total "
                      "(the other totals were not found)")
        rows.append(_row(s, "pl_base", nm.mean(), q if full else "derived", base_basis, src))
        f = g.dropna(subset=["facility_fees"])
        if len(f) >= 15:
            slope = np.polyfit(f.position, f.facility_fees, 1)[0]
            rows.append(_row(s, "pl_fac_slope", slope, q, "least-squares slope of facility fees "
                             "on league position", src))
    # 2008/09: no table found anywhere; 2009/10 was the last season of the same
    # 2007-10 TV contract, so its prices stand in (marked filled).
    # 2014/15: only five clubs' totals, four of them top-four clubs with the most TV
    # games, so their mean overstates the average club; interpolated instead.
    rows[:] = [r for r in rows if not (r["item"] == "pl_base" and r["season"] == 2014)]
    for item in ("pl_base", "pl_merit_unit"):
        _fill(rows, item)
    # facility-fee slope: seasons without per-club fees get the nearest fitted
    # season's slope scaled by the ratio of base payments
    have = {r["season"]: r["value"] for r in rows if r["item"] == "pl_fac_slope"}
    base = {r["season"]: r["value"] for r in rows if r["item"] == "pl_base"}
    for s in SEASONS:
        if s not in have:
            n = min(have, key=lambda x: (abs(x - s), x))
            rows.append(_row(s, "pl_fac_slope", have[n] * base[s] / base[n], "filled",
                             f"{n} slope scaled by the ratio of base payments"))


# ---------------------------------------------------------------- parachutes


# chosen rows of parachute_raw.csv: (season, year) -> (amount £m, status, note)
PARACHUTE_CHOICE = {
    (2009, 1): (12.4, "sourced", ""), (2009, 2): (12.4, "sourced", ""),
    (2010, 1): (16.0, "sourced", "scheme amount (16/16/8/8); Burnley accounts say about £15m"),
    (2010, 2): (16.0, "sourced", "scheme amount, 16/16/8/8"),
    (2011, 1): (15.475005, "sourced", ""),
    (2012, 1): (15.7, "sourced", "top of the stated 2012/13 range (£5.7m-£15.7m), taken as year 1"),
    (2012, 4): (5.7, "sourced", "bottom of the stated range, taken as year 4"),
    (2013, 1): (24.1, "sourced", "QPR accounts via Swiss Ramble"),
    (2014, 1): (25.0, "sourced", ""), (2014, 2): (20.0, "sourced", ""),
    (2014, 3): (10.0, "sourced", "scheme amount (25/20/10/10)"),
    (2014, 4): (10.0, "sourced", "scheme amount (25/20/10/10)"),
    (2015, 1): (25.937356, "sourced", ""), (2015, 2): (20.8, "sourced", ""),
    (2015, 3): (10.5, "sourced", ""), (2015, 4): (10.5, "sourced", ""),
    (2016, 1): (40.9, "sourced", ""), (2016, 2): (31.1, "sourced", "old-system year 2 (QPR)"),
    (2016, 3): (16.3, "sourced", "old system"), (2016, 4): (16.3, "sourced", "old system"),
    (2017, 1): (41.57, "sourced", ""), (2017, 2): (34.0, "sourced", ""),
    (2017, 3): (16.6, "sourced", "old system (QPR)"), (2017, 4): (16.6, "sourced", "old system"),
    (2018, 1): (42.6, "sourced", ""), (2018, 2): (34.9, "sourced", ""),
    (2018, 3): (15.9, "sourced", "first new-system year 3 (Aston Villa)"),
    (2018, 4): (17.0, "sourced", "old system (QPR's last payment)"),
    (2019, 1): (41.3, "estimate", "Wikipedia table marks it est."),
    (2019, 2): (33.8, "estimate", "Wikipedia est."), (2019, 3): (15.0, "estimate", "Wikipedia est."),
    (2020, 1): (43.4, "estimate", "Wikipedia est."), (2020, 2): (35.5, "estimate", "Wikipedia est."),
    (2020, 3): (15.8, "estimate", "Wikipedia est."),
    (2021, 1): (44.4, "estimate", "Wikipedia est."), (2021, 2): (36.3, "estimate", "Wikipedia est."),
    (2021, 3): (16.1, "estimate", "Wikipedia est."),
    (2022, 1): (47.6, "sourced", "EFL evidence to Parliament"),
    (2022, 2): (38.9, "sourced", "EFL evidence"), (2022, 3): (17.3, "sourced", "EFL evidence"),
    (2024, 1): (48.9, "sourced", "EFL evidence to Parliament"),
    (2024, 2): (40.1, "sourced", "EFL evidence"), (2024, 3): (17.8, "sourced", "EFL evidence"),
    (2025, 1): (49.0, "estimate", "low-confidence secondary article"),
    (2025, 2): (40.0, "estimate", "low-confidence secondary article"),
}
# Year-to-year shape of the four-year scheme when only year 1 is sourced:
# 2010-13 deal 16/16/8/8, 2013-16 deal 23/18/9/9 (Swiss Ramble).
SCHEME = {2011: (16, 16, 8, 8), 2012: (16, 16, 8, 8), 2013: (23, 18, 9, 9)}


def parachutes(rows):
    raw = pd.read_csv(SRC / "parachute_raw.csv")
    for (s, y), (v, st, note) in PARACHUTE_CHOICE.items():
        src = raw[(raw.season == s) & (raw.year_of_parachute.astype(str) == str(y))]
        src = src.source_url.iloc[0] if len(src) else \
            raw[raw.season == s].source_url.iloc[0]
        rows.append(_row(s, f"parachute_y{y}", v * 1e6, st, note, src))
    have = {(r["season"], int(r["item"][-1])): r["value"] for r in rows
            if r["item"].startswith("parachute_y")}
    for s, shape in SCHEME.items():
        for y in (2, 3, 4):
            if (s, y) not in have:
                v = have[(s, 1)] * shape[y - 1] / shape[0]
                rows.append(_row(s, f"parachute_y{y}", v, "filled",
                                 f"year 1 x {shape[y - 1]}/{shape[0]} (scheme shape of the TV deal)"))
    # 2008/09: two-year scheme; 2009/10 amount stands in (same TV deal).
    for y in (1, 2):
        rows.append(_row(2008, f"parachute_y{y}", have[(2009, y)], "filled",
                         "2009/10 amount (same 2007-10 TV deal); no 2008/09 figure found"))
    # 2009/10: no club was yet in year 3; 2010/11 year 4 not reached either.
    # 2023/24: only a low-confidence blog (~44/36/16, below both neighbours);
    # interpolated between 2022/23 and 2024/25 instead.
    for y in (1, 2, 3):
        rows.append(_row(2023, f"parachute_y{y}", (have[(2022, y)] + have[(2024, y)]) / 2, "filled",
                         "mean of 2022/23 and 2024/25 (a blog's ~44/36/16 judged unreliable)"))
    # 2025/26 year 3: 20% of the equal share as years 1-2 are 55%/45%: 20/55 of year 1.
    rows.append(_row(2025, "parachute_y3", have[(2025, 1)] * 20 / 55, "filled",
                     "20/55 of year 1 (the 55/45/20 rule)"))


def parachute_rules() -> pd.DataFrame:
    """Years of parachute by relegation season and length of PL spell (sources in
    sources/parachute_rules.md): two years up to 2007/08 relegations, three for
    2008/09 (Evans: first year-3 recipient in 2011/12), four for 2009/10-2014/15,
    then three (two after a single PL season) from 2015/16 relegations."""
    return pd.DataFrame([
        (1990, 2007, 1, 99, 2), (2008, 2008, 1, 99, 3), (2009, 2014, 1, 99, 4),
        (2015, 2099, 1, 1, 2), (2015, 2099, 2, 99, 3)],
        columns=["first_relegation", "last_relegation", "min_spell", "max_spell", "years"])


# ---------------------------------------------------------------- solidarity and EFL money

SOL_TIER = {"championship_no_parachute": 2, "league_one": 3, "league_two": 4}
EFL_TIER = {"championship": 2, "league_one": 3, "league_two": 4}


# sourced rows set aside, with the reason (assumptions log E4)
DROP = {
    ("efl_central_raw.csv", 2010, "championship"):
        "£1.0m for 2010/11 sits between £2.47m and £2.5m; the sentence it comes from is ambiguous",
    ("solidarity_raw.csv", 2009, "league_one"):
        "one club's accounts line (£0.1m), below the League Two figure of the next season",
}


def by_tier(rows, path, tiers, prefix, skip_alt=True):
    raw = pd.read_csv(SRC / path)
    col = raw.columns[1]
    amt = raw.columns[2]
    for r in raw.itertuples(index=False):
        t = tiers.get(getattr(r, col))
        v = str(getattr(r, amt))
        note = str(r.notes)
        if t is None or v in ("", "nan") or "-" in v or (path, r.season, getattr(r, col)) in DROP:
            continue
        if skip_alt and note.startswith("ALT"):
            continue
        item = f"{prefix}_t{t}"
        if any(x["item"] == item and x["season"] == r.season for x in rows):
            continue
        st = "estimate" if note.startswith(("APPROX", "ESTIMATE")) else "sourced"
        rows.append(_row(r.season, item, float(v), st, note[:200], r.source_url))


def solidarity(rows):
    # 2008/09: £1m per Championship club from 2006/07 (Wikipedia, in the 2009 row's note)
    raw = pd.read_csv(SRC / "solidarity_raw.csv")
    src = raw[raw.season == 2009].source_url.iloc[0]
    rows.append(_row(2008, "solidarity_t2", 1e6, "sourced",
                     "£1m per Championship club from 2006/07 (Wikipedia, cited in the 2009/10 note)",
                     src))
    by_tier(rows, "solidarity_raw.csv", SOL_TIER, "solidarity")
    # 2020/21: only the total, £79m to 19 Championship clubs
    s20 = raw[(raw.season == 2020)].source_url.iloc[0]
    rows.append(_row(2020, "solidarity_t2", 79e6 / 19, "derived", "£79m total / 19 clubs", s20))
    for t in (2, 3, 4):
        _fill(rows, f"solidarity_t{t}")


def efl_central(rows):
    by_tier(rows, "efl_central_raw.csv", EFL_TIER, "efl")
    raw = pd.read_csv(SRC / "efl_central_raw.csv")
    src = raw[raw.season == 2024].source_url.iloc[0]
    for t, lo, hi in ((2, 4.6e6, 5.0e6), (3, 1.0e6, 1.2e6), (4, 0.8e6, 1.0e6)):
        rows.append(_row(2024, f"efl_t{t}", (lo + hi) / 2, "estimate",
                         f"midpoint of the stated range £{lo/1e6:.1f}m-£{hi/1e6:.1f}m", src))
    for t in (2, 3, 4):
        _fill(rows, f"efl_t{t}")


# ---------------------------------------------------------------- UEFA


def uefa(rows, fx: dict):
    """Expected UEFA prize money (£) for an English club entering each competition in
    a season: the average of the English clubs' sourced UEFA payments that season,
    converted at the season's average rate."""
    p = pd.read_csv(SRC / "uefa_payments.csv")
    p = p[p.competition.isin(["UCL", "UEL", "UECL"]) & p.amount_eur.notna()]
    for (s, comp), g in p.groupby(["competition_season", "competition"]):
        complete = len(g)
        rate = fx[s]
        rows.append(_row(s, f"uefa_{comp}", g.amount_eur.mean() * rate,
                         "derived", f"mean of {complete} English clubs' UEFA payments x "
                         f"{rate:.4f} GBP/EUR", g.source_url.iloc[0]))
    for comp in ("UCL", "UEL", "UECL"):
        _fill(rows, f"uefa_{comp}", [s for s in SEASONS if s >= (2021 if comp == "UECL" else 2008)])


def uefa_places() -> pd.DataFrame:
    """Competition earned by each PL position each season, through the league
    table only (places passed down from cup winners included, since they go to the
    next league position; cup, fair-play and title-holder places are left out: the
    same club qualifies the same way in a scenario and the real world)."""
    e = pd.read_csv(SRC / "euro_places.csv")
    e = e[e.route.isin(["league", "passed_down_from_cup", "european_performance_spot",
                        "league_displaced_by_ucl_holder"])]
    rows = []
    for r in e.itertuples(index=False):
        for p in range(int(r.position_from), int(r.position_to) + 1):
            rows.append((r.league_season, p, r.competition, r.stage, r.route))
    return pd.DataFrame(rows, columns=["season", "position", "competition", "stage", "route"])


# ---------------------------------------------------------------- CPI and FX


def season_cpi() -> pd.Series:
    """CPI (ONS D7BT) averaged over August-May of each season."""
    c = pd.read_csv(SRC / "cpi.csv")
    m = c[c.period.str.contains("-")].copy()
    m["y"] = m.period.str[:4].astype(int)
    m["mo"] = m.period.str[5:7].astype(int)
    out = {}
    for s in range(2008, LAST_SEASON + 1):
        sel = ((m.y == s) & (m.mo >= 8)) | ((m.y == s + 1) & (m.mo <= 5))
        if sel.sum() == 10:
            out[s] = m[sel].cpi_index.mean()
    return pd.Series(out)


def _season_mean(path, col) -> dict:
    """Mean of a monthly series over August-May of each season."""
    c = pd.read_csv(SRC / path)
    m = c[c.period.astype(str).str.contains("-")].copy()
    m["y"] = m.period.str[:4].astype(int)
    m["mo"] = m.period.str[5:7].astype(int)
    out = {}
    for s in range(2008, LAST_SEASON + 1):
        sel = ((m.y == s) & (m.mo >= 8)) | ((m.y == s + 1) & (m.mo <= 5))
        if sel.sum() == 10:
            out[s] = float(m[sel][col].mean())
    return out


def season_cpi() -> dict:
    """CPI (ONS D7BT, 2015=100) averaged over August-May of each season."""
    return _season_mean("cpi.csv", "cpi_index")


def season_fx() -> dict:
    """GBP per EUR (ECB reference rate, monthly averages via the Bundesbank)
    averaged over August-May of each season."""
    return _season_mean("fx.csv", "gbp_per_eur")


# ---------------------------------------------------------------- matchday and commercial

COVID = {2019, 2020}   # seasons with matches behind closed doors: matchday income distorted
DIVS = {"Premier League": 1, "Championship": 2, "League One": 3, "League Two": 4}


def division_moves() -> pd.DataFrame:
    """Every club in the accounts table seen in two consecutive seasons in adjacent
    divisions: the change in matchday plus commercial revenue, in 2025/26 pounds.
    Seasons hit by Covid (2019/20, 2020/21) are left out."""
    from altpl.clubs import club_id
    cpi = season_cpi()
    d = pd.read_csv(SRC / "club_revenue.csv")
    d = d[d.division.isin(DIVS)].copy()
    d["tier"] = d.division.map(DIVS)
    d["mc"] = d.matchday + d.commercial
    d = d.dropna(subset=["mc"]).drop_duplicates(["club", "season"])
    d["club_id"] = [club_id(c, s) for c, s in zip(d.club, d.season)]
    d = d.set_index(["club_id", "season"])
    rows = []
    for (c, s), r in d.iterrows():
        if (c, s + 1) not in d.index or {s, s + 1} & COVID:
            continue
        n = d.loc[(c, s + 1)]
        if abs(n.tier - r.tier) != 1:
            continue
        up = n.tier < r.tier
        hi, lo = (n, r) if up else (r, n)
        gain = (hi.mc - lo.mc) * cpi[LAST_SEASON] / cpi[s + 1]
        rows.append(dict(club_id=c, club=r.club, season=s + 1, move="promoted" if up else "relegated",
                         upper_tier=int(min(n.tier, r.tier)), mc_before=r.mc, mc_after=n.mc,
                         gain_2025gbp=gain, source=f"{r.source_url} ; {n.source_url}"))
    return pd.DataFrame(rows)


def uplift() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Matchday + commercial gain per division climbed, by season (nominal pounds).

    - PL vs Championship: the clubs' own accounts around promotion and relegation
      (both directions pooled), a straight-line trend in real terms over seasons.
    - Championship vs League One: the mean of the few promotions in the accounts
      table, constant in real terms.
    - League One vs League Two and League Two vs National League: no usable accounts
      (one League Two club, Wrexham, is unrepresentative); the step below is scaled
      by the ratio of League Two to League One average revenue (Deloitte), marked
      filled.
    """
    mv = division_moves()
    cpi = season_cpi()
    out = []
    pl = mv[mv.upper_tier == 1]
    a, b = np.polyfit(pl.season, pl.gain_2025gbp, 1)
    l1 = mv[mv.upper_tier == 2]
    step2 = l1.gain_2025gbp.mean()
    dv = pd.read_csv(SRC / "division_revenue.csv")
    avg = dv[dv.division.isin(["League One", "League Two"])].dropna(subset=["average_revenue"])
    avg = avg.pivot_table(index="season", columns="division", values="average_revenue")
    ratio = float((avg["League Two"] / avg["League One"]).dropna().mean())
    for s in SEASONS:
        f = cpi[s] / cpi[LAST_SEASON]
        g1 = (a * s + b) * f
        out += [dict(season=s, tier=1, step_gain=g1, status="derived",
                     basis=f"linear trend in real terms over {len(pl)} PL/Championship moves"),
                dict(season=s, tier=2, step_gain=step2 * f, status="derived",
                     basis=f"mean of {len(l1)} Championship/League One moves, constant in real terms"),
                dict(season=s, tier=3, step_gain=step2 * ratio * f, status="filled",
                     basis=f"step above x {ratio:.2f} (League Two / League One average revenue, Deloitte)"),
                dict(season=s, tier=4, step_gain=step2 * ratio ** 2 * f, status="filled",
                     basis=f"step above x {ratio:.2f} again (no National League evidence)")]
    return pd.DataFrame(out), mv


# ---------------------------------------------------------------- build


def build() -> pd.DataFrame:
    rows = []
    pl_central(rows)
    parachutes(rows)
    solidarity(rows)
    efl_central(rows)
    uefa(rows, season_fx())
    for s, v in season_cpi().items():
        rows.append(_row(s, "cpi", v, "derived", "mean of ONS D7BT monthly index, Aug-May",
                         "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7bt"))
    out = pd.DataFrame(rows).sort_values(["item", "season"], ignore_index=True)
    return out


def main():
    p = build()
    p.to_csv(PROCESSED / "finance_prices.csv", index=False)
    uefa_places().to_csv(PROCESSED / "finance_uefa_places.csv", index=False)
    parachute_rules().to_csv(PROCESSED / "finance_parachute_rules.csv", index=False)
    up, mv = uplift()
    up.to_csv(PROCESSED / "finance_uplift.csv", index=False)
    mv.to_csv(PROCESSED / "finance_division_moves.csv", index=False)
    print(mv.drop(columns="source").round(0).to_string())
    print(up[up.season.isin([2008, 2016, 2025])].round(0).to_string())
    print(p.pivot_table(index="season", columns="item", values="value").round(0).to_string())
    print(p.status.value_counts())


if __name__ == "__main__":
    main()
