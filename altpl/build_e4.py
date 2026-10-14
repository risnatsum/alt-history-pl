"""Stage E4 pipeline: build the price list and test the finance model.

    python -m altpl.build_e4              # 10,000 runs for the example (about 30 minutes)
    python -m altpl.build_e4 --runs 1000  # quicker look

1. Price list: every sourced figure turned into one value per season and item,
   with how much to trust it (``altpl.finance_data``).
2. Reproduction: reality with every real result kept gives a revenue difference of
   exactly zero for every club and season.
3. Parachutes: the clubs the model pays in each real season against the sourced
   recipient lists and counts.
4. PL central payments: the model's payment by position against each club's
   sourced payment.
5. Real promotion and relegation seasons: the model's change in a club's revenue
   against the change in its published accounts.
6. Example: the finance tables for reality fully simulated 2008/09-2025/26 (the E3
   knock-on run), to show the outputs. Not a scenario.
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from altpl import finance as F
from altpl import finance_data as FD
from altpl import outputs as O
from altpl import simulator as S
from altpl.build_e3 import _md
from altpl.clubs import club_id, club_name
from altpl.config import LAST_SEASON, PROCESSED, ROOT, season_label

SEASONS = list(range(2008, LAST_SEASON + 1))

# Parachute recipients stated by sources (data/reference/finance/sources):
# counts from sportingintelligence 2009/10, 2011/12, 2012/13; club lists from the
# Sky Sports 2016/17 table and sportingintelligence 2017/18.
PARACHUTE_FACTS = {
    2009: 5, 2011: 7, 2012: 8,
    2016: {"aston_villa", "newcastle_united", "norwich_city", "queens_park_rangers",
           "cardiff_city", "fulham", "reading", "wigan_athletic"},
    2017: {"sunderland", "hull_city", "middlesbrough", "aston_villa", "norwich_city",
           "cardiff_city", "fulham", "queens_park_rangers"},
}


def real_revenue(R: S.Reality, P: F.Prices) -> pd.DataFrame:
    rt, rp = F.real_arrays(R, SEASONS)
    rb, rp1 = F._history_inputs(R, SEASONS, 1)
    rows = []
    for j, o in F.revenue(P, SEASONS, rt, rp, rb, rp1):
        for c in np.flatnonzero(rt[0, j] > 0):
            rows.append(dict(season=SEASONS[j], club_id=R.clubs[c], tier=int(rt[0, j, c]),
                             pos=int(rp[0, j, c]), **{k: o[k][0, c] for k in F.COMPONENTS}))
    m = pd.DataFrame(rows)
    m["total"] = m[list(F.COMPONENTS)].sum(axis=1)
    return m


def parachute_check(m: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for s, fact in PARACHUTE_FACTS.items():
        got = set(m[(m.season == s) & (m.parachute > 0)].club_id)
        if isinstance(fact, int):
            rows.append(dict(season=season_label(s), sourced=f"{fact} clubs", model=f"{len(got)} clubs",
                             match=len(got) == fact))
        else:
            rows.append(dict(season=season_label(s), sourced=", ".join(sorted(club_name(c) for c in fact)),
                             model=", ".join(sorted(club_name(c) for c in got)), match=got == fact))
    return pd.DataFrame(rows)


def central_check(m: pd.DataFrame) -> pd.DataFrame:
    pl = pd.read_csv(FD.SRC / "pl_payments.csv").dropna(subset=["total"])
    pl["club_id"] = [club_id(c, s) for c, s in zip(pl.club, pl.season)]
    x = pl.merge(m[["season", "club_id", "pos", "pl_central"]], on=["season", "club_id"])
    x["error"] = x.pl_central - x.total
    return x[["season", "club", "position", "total", "pl_central", "error", "source_url"]]


def move_test(m: pd.DataFrame) -> pd.DataFrame:
    """Every club with published revenue in two consecutive seasons that changed
    division: change in revenue, accounts vs model."""
    acc = pd.read_csv(FD.SRC / "club_revenue.csv").dropna(subset=["total"])
    acc["club_id"] = [club_id(c, s) for c, s in zip(acc.club, acc.season)]
    acc = acc.drop_duplicates(["club_id", "season"])
    a = acc.merge(m, on=["season", "club_id"], suffixes=("_accounts", "")).set_index(["club_id", "season"])
    out = []
    for (c, s), r in a.iterrows():
        if (c, s - 1) not in a.index:
            continue
        p = a.loc[(c, s - 1)]
        if p.tier == r.tier:
            continue
        out.append(dict(
            club=club_name(c), season=season_label(s), season_start=s,
            move=f"{O.DIV[p.tier]} to {O.DIV[r.tier]}",
            covid=bool({s - 1, s} & FD.COVID),
            accounts_before=p.total_accounts, accounts_after=r.total_accounts,
            accounts_change=r.total_accounts - p.total_accounts,
            model_before=p.total, model_after=r.total, model_change=r.total - p.total,
            source=f"{p.source_url} ; {r.source_url}"))
    o = pd.DataFrame(out)
    o["error"] = o.model_change - o.accounts_change
    return o


def move_summary(o: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (mv, cov), g in o.groupby(["move", "covid"]):
        rows.append(dict(move=mv, covid_seasons=cov, cases=len(g),
                         accounts_change_avg=g.accounts_change.mean() / 1e6,
                         model_change_avg=g.model_change.mean() / 1e6,
                         bias=g.error.mean() / 1e6, mean_abs_error=g.error.abs().mean() / 1e6,
                         share_error_within_10pct=(g.error.abs() <= 0.1 * g.accounts_change.abs()).mean()))
    return pd.DataFrame(rows).sort_values(["covid_seasons", "cases"], ascending=[True, False])


def main(runs: int):
    t0 = time.time()
    print("1. price list", flush=True)
    FD.main()
    P = F.Prices()
    R = S.Reality()

    print("2. reproduction", flush=True)
    rep = S.simulate(S.real_world(R), runs=20, reality=R)
    fr0 = F.finance(rep, R, P)
    rep_ok = float(fr0.club_season.diff_mean.abs().max() if len(fr0.club_season) else 0.0)

    print("3-5. checks against sources", flush=True)
    m = real_revenue(R, P)
    para = parachute_check(m)
    cen = central_check(m)
    mv = move_test(m)
    msum = move_summary(mv)

    print("6. example: reality fully simulated", flush=True)
    w = S.real_world(R)
    w.name = "reality, fully simulated (example, not a scenario)"
    sim = S.simulate(w, runs=runs, seed=S.SEED + 2000, anchored=False, reality=R)
    fr = F.finance(sim, R, P)
    head = F.headline(fr, 15)

    prices = pd.read_csv(PROCESSED / "finance_prices.csv")
    with pd.ExcelWriter(PROCESSED / "e4_backtest.xlsx") as xw:
        prices.to_excel(xw, sheet_name="price_list", index=False)
        pd.read_csv(PROCESSED / "finance_uplift.csv").to_excel(xw, sheet_name="matchday_commercial", index=False)
        pd.read_csv(PROCESSED / "finance_division_moves.csv").to_excel(xw, sheet_name="accounts_moves", index=False)
        pd.read_csv(PROCESSED / "finance_uefa_places.csv").to_excel(xw, sheet_name="uefa_places", index=False)
        pd.read_csv(PROCESSED / "finance_parachute_rules.csv").to_excel(xw, sheet_name="parachute_rules", index=False)
        para.to_excel(xw, sheet_name="parachute_check", index=False)
        cen.to_excel(xw, sheet_name="central_check", index=False)
        mv.to_excel(xw, sheet_name="promotion_test", index=False)
        msum.to_excel(xw, sheet_name="promotion_summary", index=False)
        m.to_excel(xw, sheet_name="real_revenue_model", index=False)
    O.write_workbook(sim, R, PROCESSED / "e4_finance_example.xlsx", extra=F.write_sheets(fr))
    write_report(prices, rep_ok, para, cen, mv, msum, head, fr, runs, time.time() - t0)
    print(f"done in {time.time() - t0:.0f}s")


EXAMPLES = [("Burnley", "2014/15"), ("Bournemouth", "2015/16"), ("Huddersfield Town", "2017/18"),
            ("Brentford", "2021/22"), ("Luton Town", "2023/24"), ("Ipswich Town", "2024/25"),
            ("Hull City", "2017/18"), ("Leicester City", "2023/24"), ("Plymouth Argyle", "2023/24"),
            ("Portsmouth", "2024/25")]


def write_report(prices, rep_ok, para, cen, mv, msum, head, fr, runs, secs):
    st = prices.pivot_table(index="item", columns="status", values="value", aggfunc="size",
                            fill_value=0).reset_index()
    filled = prices[prices.status == "filled"].groupby("item").season.apply(
        lambda x: ", ".join(season_label(s) for s in sorted(x))).reset_index(name="filled seasons")
    st = st.merge(filled, on="item", how="left").fillna({"filled seasons": ""})
    cs = cen.assign(abs_error=cen.error.abs()).groupby("season").agg(
        clubs=("error", "size"), mean_abs_error=("abs_error", "mean"), bias=("error", "mean")).reset_index()
    cs["season"] = cs.season.map(season_label)
    for c in ("mean_abs_error", "bias"):
        cs[c] = cs[c] / 1e6
    ex = mv.set_index(["club", "season"]).reindex(EXAMPLES).dropna(subset=["move"]).reset_index()
    ex = ex[["club", "season", "move", "accounts_change", "model_change", "error"]]
    for c in ("accounts_change", "model_change", "error"):
        ex[c] = ex[c] / 1e6
    ct = fr.club_total
    L = [
        "# E4 validation report", "",
        "Generated by `python -m altpl.build_e4`. Do not edit by hand. Every model number is an "
        "estimate, not a fact.", "",
        f"Full tables: `data/processed/e4_backtest.xlsx` (price list, checks) and "
        f"`data/processed/e4_finance_example.xlsx` (standard outputs plus finance sheets for the "
        f"example run, {runs:,} runs). {secs / 60:.0f} minutes.", "",
        "## How the model works", "",
        "For every run, season and club the model prices where the club played and finished, "
        "then subtracts what the same model gives for where it really played and finished. "
        "Components: PL central payments by position (base payment, merit per place, facility-fee "
        "slope), parachute payments under the rules of the season the club went down, PL "
        "solidarity payments, the EFL's own central distribution, UEFA prize money for European "
        "places earned through the PL table, and matchday plus commercial revenue gained per "
        "division climbed. Nominal pounds of the season paid, and 2025/26 pounds with the ONS CPI.", "",
        "## 1. Price list: where every number comes from", "",
        "Sourced figures are in `data/reference/finance/sources/` with the URL of every row. "
        "None was typed from memory. No official PL table could be read directly (they are "
        "published as images), so PL payments come from pages that reproduce them "
        "(sportingintelligence, Sky Sports, CityAM, salarysport and others). Rows per item by "
        "status (`sourced`, `derived` = arithmetic on sourced figures, `estimate` = a source's "
        "own estimate, `filled` = no source, value from a stated fill rule):", "",
        _md(st), "",
        "## 2. Reproducing reality", "",
        f"Reality with every real result kept: the largest revenue difference from reality over "
        f"every club and season is £{rep_ok:,.0f}.", "",
        "## 3. Parachute recipients", "",
        "Which clubs the model pays, from real PL membership (back to 2000/01) and the rules:", "",
        _md(para), "",
        "## 4. PL central payments by position", "",
        "The model's payment for a club's real position against its sourced payment (£m). "
        "The error is mostly facility fees, which follow how often a club is on TV rather than "
        "its position:", "",
        _md(cs, {"mean_abs_error": "{:.1f}", "bias": "{:.1f}"}), "",
        "## 5. Real promotion and relegation seasons", "",
        "Change in total revenue from the season before a move to the season of it: the clubs' "
        "published accounts against the model, £m. Accounts years and seasons do not always "
        "line up, accounts include income the model leaves out (player loans, cup runs, "
        "other income), and the Covid seasons (2019/20 and 2020/21: rebates to broadcasters, "
        "empty grounds, 13-month accounts) are shown separately.", "",
        _md(msum, {"accounts_change_avg": "{:.1f}", "model_change_avg": "{:.1f}", "bias": "{:.1f}",
                   "mean_abs_error": "{:.1f}", "share_error_within_10pct": "{:.0%}"}), "",
        "A few clubs:", "",
        _md(ex, {"accounts_change": "{:+.1f}", "model_change": "{:+.1f}", "error": "{:+.1f}"}), "",
        "## 6. Example outputs: reality fully simulated", "",
        "Every season replayed from 2008/09 with each run carrying its own promotions and "
        "relegations (the E3 knock-on run). This is not a scenario, only a demonstration of "
        "the finance outputs; clubs gain or lose here only through the luck of the draw. "
        f"{len(ct)} clubs differ from reality in at least 5% of runs in some season. Largest "
        "expected gains and losses over 2008/09-2025/26, £m in 2025/26 pounds (5th-95th "
        "percentile range):", "",
        _md(head, {"gain_gbp_m_2025": "{:+.0f}", "p05": "{:+.0f}", "p95": "{:+.0f}",
                   "gain_gbp_m_nominal": "{:+.0f}"}), "",
    ]
    (ROOT / "docs" / "e4_validation.md").write_text("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10_000)
    main(ap.parse_args().runs)
