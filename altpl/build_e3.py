"""Stage E3 pipeline: test the season simulator by re-simulating real seasons.

    python -m altpl.build_e3              # 10,000 runs per test (about 20 minutes)
    python -m altpl.build_e3 --runs 1000  # quicker look

1. Reproduction: reality with every real result kept must give back every real
   table and every real promotion and relegation, in every run.
2. Single seasons, fully simulated: each season replayed from scratch with its own
   ratings and real membership; are title, promotion, play-off and relegation odds
   about right, and do real points fall inside the 5-95% ranges?
3. Single seasons, a fifth of the fixtures hidden: ratings refitted without them,
   the hidden fifth simulated and the rest kept. This is the scenario situation
   (most fixtures real, some never happened).
4. Knock-on: 2008/09 to 2025/26 fully simulated with each run carrying its own
   promotions and relegations; plus the step-up and money sensitivities.
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from altpl import outputs as O
from altpl import simulator as S
from altpl.config import FIRST_SEASON, LAST_SEASON, PROCESSED, ROOT, season_label
from altpl.ratings import fit, load_matches

EVENTS = ["title", "auto", "promoted", "playoff_place", "relegated"]


def real_flags(reality: S.Reality) -> pd.DataFrame:
    t = reality.tables.copy()
    r = reality.rules
    t["auto_up"] = [r.loc[(s, k)].auto_up for s, k in zip(t.season, t.tier)]
    t["pf"] = [r.loc[(s, k)].playoff_from if r.loc[(s, k)].playoff_up else 0 for s, k in zip(t.season, t.tier)]
    t["pt"] = [r.loc[(s, k)].playoff_to if r.loc[(s, k)].playoff_up else 0 for s, k in zip(t.season, t.tier)]
    o = t.outcome.fillna("")
    t["title"] = t.pos == 1
    t["auto"] = o == "promoted"
    t["promoted"] = o.str.startswith("promoted")
    t["playoff_place"] = (t.pos >= t.pf) & (t.pos <= t.pt)
    t["relegated"] = o == "relegated"
    return t[["season", "tier", "club_id", "pts", "pos"] + EVENTS]


def season_frame(sim: S.Simulation, reality: S.Reality, flags: pd.DataFrame) -> pd.DataFrame:
    """Simulated vs real for every real club-season (club in its real division)."""
    e = O.expected_tables(sim, reality)
    e = e.rename(columns={"p_auto_promotion": "p_auto", "p_playoffs": "p_playoff_place"})
    for c in ["p_auto", "p_promoted", "p_playoff_place"]:
        if c not in e:
            e[c] = np.nan
    e.loc[e.tier == 1, ["p_auto", "p_promoted", "p_playoff_place"]] = np.nan
    m = flags.merge(e, on=["season", "tier", "club_id"], how="inner", suffixes=("", "_e"))
    return m


def metrics(m: pd.DataFrame, label: str) -> dict:
    out = {"test": label, "club_seasons": len(m),
           "pts_in_5_95": ((m.pts >= m.pts_p05) & (m.pts <= m.pts_p95)).mean(),
           "pts_mae": (m.xpts - m.pts).abs().mean(),
           "pos_mae": (m.xpos - m.pos).abs().mean()}
    for ev in EVENTS:
        g = m[m[f"p_{ev}"].notna()]
        g = g[g.groupby(["season", "tier"])[ev].transform("sum") > 0]  # divisions with the event
        if not len(g):
            continue
        p, y = g[f"p_{ev}"].values, g[ev].values.astype(float)
        base = g.groupby(["season", "tier"])[ev].transform("mean").values
        out[f"{ev}_expected"] = p.sum()
        out[f"{ev}_happened"] = y.sum()
        out[f"{ev}_brier_skill"] = 1 - ((p - y) ** 2).mean() / ((base - y) ** 2).mean()
    return out


def calibration(m: pd.DataFrame, label: str) -> pd.DataFrame:
    rows = []
    edges = [0, .02, .05, .1, .2, .3, .5, .7, .9, 1.0001]
    for ev in EVENTS:
        g = m[m[f"p_{ev}"].notna()]
        b = pd.cut(g[f"p_{ev}"], edges, right=False)
        c = g.groupby(b, observed=True).agg(n=(ev, "size"), predicted=(f"p_{ev}", "mean"),
                                            observed=(ev, "mean")).reset_index()
        c["bin"] = c[f"p_{ev}"].astype(str)
        rows.append(c.drop(columns=f"p_{ev}").assign(event=ev, test=label))
    return pd.concat(rows, ignore_index=True)


def single_seasons(reality, flags, runs, anchored, label, seed):
    frames = []
    for s in range(FIRST_SEASON, LAST_SEASON + 1):
        w = S.real_world(reality, s, s)
        sim = S.simulate(w, runs=runs, seed=seed + s, anchored=anchored, reality=reality)
        frames.append(season_frame(sim, reality, flags))
        print(f"  {label} {season_label(s)}", flush=True)
    return pd.concat(frames, ignore_index=True)


def holdout_reality(frac=0.2, seed=S.SEED):
    """Reality with a random fifth of the real results removed and ratings refitted
    without them (scores and odds of hidden matches unused)."""
    R = S.Reality()
    m = load_matches()
    rng = np.random.default_rng(seed)
    hide = rng.random(len(m)) < frac
    r = fit(m, sigma=R.params["sigma"], omega=R.params["omega"], weight=(~hide).astype(float))
    R.use_ratings(r.teams, {"mu": r.mu, "rho": r.rho, "sigma": r.sigma, "omega": r.omega,
                            "home_season": r.home_season, "home_tier": r.home_tier})
    h = m[hide]
    si = h.season.values - FIRST_SEASON
    hi, ai = h.home_id.map(R.ci).values, h.away_id.map(R.ci).values
    R.real_hg[si, hi, ai] = -1
    R.real_ag[si, hi, ai] = -1
    R.real_div[si, hi, ai] = 0
    return R, int(hide.sum()), len(m)


def knock_on(reality, runs, seed, **kw):
    w = S.real_world(reality)
    for k, v in kw.items():
        setattr(w, k, v)
    w.name = "reality, fully simulated" + "".join(f", {k}={v}" for k, v in kw.items())
    return S.simulate(w, runs=runs, seed=seed, anchored=False, reality=reality)


def promoted_points(sim, reality, label):
    """PL points and survival of clubs that were in the Championship the season
    before: in reality, and in the run split by whether the club really was in the PL
    that season (so rated from a PL season) or not (rated from its Championship
    season, the cross-division case)."""
    n = len(sim.seasons)
    j = np.arange(1, n)
    rt = reality.tier
    up = (sim.tier[:, j] == 1) & (sim.tier[:, j - 1] == 2)
    stay = sim.tier[:, j + 1] == 1
    has_next = sim.tier[:, n].any()
    really = (rt[j] == 1)[None, :, :]
    rows = []
    for name, mask in (("run promoted, really in PL that season", up & really),
                       ("run promoted, not really in PL (Championship rating)", up & ~really)):
        rows.append({"variant": label, "clubs": name, "club_seasons_per_run": mask.sum() / sim.runs,
                     "avg_pts": sim.pts[:, j][mask].mean(),
                     "stayed_up": stay[mask].mean() if has_next else np.nan})
    real_up = (rt[1:n] == 1) & (rt[0:n - 1] == 2)
    t = reality.tables.set_index(["season", "club_id"])
    rp, rs = [], []
    for jj, c in zip(*np.nonzero(real_up)):
        rp.append(t.loc[(sim.seasons[jj + 1], reality.clubs[c])].pts)
        rs.append(rt[jj + 2, c] == 1)
    rows.append({"variant": "reality", "clubs": "really promoted (real results)",
                 "club_seasons_per_run": len(rp), "avg_pts": np.mean(rp), "stayed_up": np.mean(rs)})
    return rows


def membership_check(sim, reality):
    rows = []
    for j, s in enumerate(sim.seasons):
        for k in S.TIERS:
            n = (sim.tier[:, j] == k).sum(1)
            rows.append({"season": season_label(s), "tier": k, "real": reality.sizes[(s, k)],
                         "sim_min": n.min(), "sim_max": n.max(),
                         "runs_not_real_size": (n != reality.sizes[(s, k)]).mean()})
    return pd.DataFrame(rows)


def main(runs: int):
    t0 = time.time()
    R = S.Reality()
    flags = real_flags(R)
    out = {}

    print("1. reproduction", flush=True)
    rep = S.simulate(S.real_world(R), runs=min(runs, 200), anchored=True, reality=R)
    real_t = R.tier[:rep.tier.shape[1]]
    mem_ok = (rep.tier == real_t[None]).all()
    tt = R.tables
    jj = tt.season.values - FIRST_SEASON
    cc = tt.club_id.map(R.ci).values
    pts_ok = (rep.pts[:, jj, cc] == tt.pts.values[None]).all()
    pos_ok = ((rep.pos[:, jj, cc] == tt.pos.values[None]) | tt.tied.values[None]).all()
    out["reproduction"] = {"runs": rep.runs, "membership_identical": bool(mem_ok),
                           "points_identical": bool(pts_ok), "positions_identical": bool(pos_ok),
                           "club_seasons": len(tt)}

    print("2. single seasons, fully simulated", flush=True)
    full = single_seasons(R, flags, runs, False, "full", S.SEED)
    print("3. single seasons, a fifth hidden", flush=True)
    RH, hidden, total = holdout_reality()
    hold = single_seasons(RH, flags, runs, True, "holdout", S.SEED + 1000)
    out["hidden"] = (hidden, total)

    print("4. knock-on", flush=True)
    base = knock_on(R, runs, S.SEED + 2000)
    step = knock_on(R, runs, S.SEED + 2000, step_up=0.1)
    money = knock_on(R, runs, S.SEED + 2000, money_boost=0.1)
    ko = pd.DataFrame(promoted_points(base, R, "default (no adjustment)")[:2]
                      + promoted_points(step, R, "step-up penalty 0.1")[:2]
                      + promoted_points(money, R, "money boost 0.1")
                      )
    sizes = membership_check(base, R)
    rt = R.tier[:base.tier.shape[1] - 1]
    share = pd.DataFrame({"season": [season_label(s) for s in base.seasons],
                          "share_in_real_division": [((base.tier[:, j] == rt[j])[:, rt[j] > 0]).mean()
                                                     for j in range(len(base.seasons))]})

    summ = pd.DataFrame([metrics(full, "single season, fully simulated"),
                         metrics(hold, "single season, a fifth of fixtures hidden")])
    by_tier = pd.DataFrame([metrics(g, f"{lab} / {O.DIV[k]}") for lab, d in
                            (("fully simulated", full), ("fifth hidden", hold))
                            for k, g in d.groupby("tier")])
    cal = pd.concat([calibration(full, "fully simulated"), calibration(hold, "fifth hidden")])

    PROCESSED.mkdir(exist_ok=True)
    with pd.ExcelWriter(PROCESSED / "e3_backtest.xlsx") as xw:
        summ.to_excel(xw, sheet_name="summary", index=False)
        by_tier.to_excel(xw, sheet_name="by_division", index=False)
        cal.to_excel(xw, sheet_name="calibration", index=False)
        full.to_excel(xw, sheet_name="full_club_seasons", index=False)
        hold.to_excel(xw, sheet_name="hidden_club_seasons", index=False)
        ko.to_excel(xw, sheet_name="knock_on_promoted", index=False)
        sizes.to_excel(xw, sheet_name="knock_on_sizes", index=False)
        share.to_excel(xw, sheet_name="knock_on_share", index=False)
    O.write_workbook(base, R, PROCESSED / "e3_knock_on_example.xlsx")
    write_report(out, summ, by_tier, cal, ko, sizes, share, runs, time.time() - t0)
    print(f"done in {time.time() - t0:.0f}s")


def _md(df: pd.DataFrame, fmt: dict | None = None) -> str:
    fmt = fmt or {}
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        cells = []
        for c, v in zip(cols, r):
            f = fmt.get(c)
            cells.append(f.format(v) if f and pd.notna(v) else ("" if pd.isna(v) else str(v)))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(out, summ, by_tier, cal, ko, sizes, share, runs, secs):
    rep = out["reproduction"]
    hidden, total = out["hidden"]
    ev_rows = []
    for _, r in summ.iterrows():
        for ev in EVENTS:
            if f"{ev}_expected" in r and pd.notna(r[f"{ev}_expected"]):
                ev_rows.append({"test": r.test, "event": ev,
                                "expected (sum of chances)": r[f"{ev}_expected"],
                                "happened": r[f"{ev}_happened"],
                                "Brier skill vs base rate": r[f"{ev}_brier_skill"]})
    ev = pd.DataFrame(ev_rows)
    sz = sizes[sizes.runs_not_real_size > 0]
    L = [
        "# E3 validation report", "",
        "Generated by `python -m altpl.build_e3`. Do not edit by hand. Every simulated number "
        "is a model estimate.", "",
        f"{runs:,} runs per test, fixed seeds; {secs / 60:.0f} minutes. Full tables in "
        "`data/processed/e3_backtest.xlsx`; the standard output workbook for the knock-on run "
        "is `data/processed/e3_knock_on_example.xlsx`.", "",
        "## 1. Reproducing reality", "",
        f"Reality simulated with every real result kept ({rep['runs']} runs, 2008/09 to 2025/26): "
        f"every final table {'matches' if rep['points_identical'] and rep['positions_identical'] else 'DOES NOT match'} "
        f"reality ({rep['club_seasons']:,} club-seasons, points and positions; tied clubs may swap), and "
        f"every run's divisions {'match' if rep['membership_identical'] else 'DO NOT match'} real membership in every "
        "season, including the expulsions, demotions, reprieves and the 2019/20 points-per-game "
        "seasons. Play-offs reproduce through the real winners.", "",
        "## 2 and 3. Re-simulating single seasons", "",
        "Each season replayed with its real clubs. *Fully simulated*: every fixture drawn from "
        "the season's own ratings. *A fifth hidden*: "
        f"{hidden:,} of {total:,} real matches (20%) hidden, ratings refitted without them, the "
        "hidden matches simulated and the rest kept. Brier skill compares each probability with "
        "a flat guess at the division's base rate (1 = perfect, 0 = no better).", "",
        _md(summ[["test", "club_seasons", "pts_in_5_95", "pts_mae", "pos_mae"]].rename(columns={
            "pts_in_5_95": "real points inside 5-95% range", "pts_mae": "points error (mean abs)",
            "pos_mae": "position error (mean abs)"}),
            {"real points inside 5-95% range": "{:.1%}", "points error (mean abs)": "{:.1f}",
             "position error (mean abs)": "{:.2f}"}), "",
        _md(ev, {"expected (sum of chances)": "{:.1f}", "happened": "{:.0f}",
                 "Brier skill vs base rate": "{:.2f}"}), "",
        "By division:", "",
        _md(by_tier[["test", "club_seasons", "pts_in_5_95", "pts_mae", "pos_mae"]],
            {"pts_in_5_95": "{:.1%}", "pts_mae": "{:.1f}", "pos_mae": "{:.2f}"}), "",
        "Calibration, all events pooled (predicted chance vs how often it happened):", "",
        _md(cal.groupby(["test", "bin"], observed=True, sort=False)
            .apply(lambda g: pd.Series({"n": g.n.sum(),
                                        "predicted": (g.predicted * g.n).sum() / g.n.sum(),
                                        "observed": (g.observed * g.n).sum() / g.n.sum()}),
                   include_groups=False).reset_index(),
            {"n": "{:.0f}", "predicted": "{:.3f}", "observed": "{:.3f}"}), "",
        "Fully simulated seasons are cautious: real points fall outside the 5-95% range "
        "less often than the 10% they should, and confident predictions come true more often "
        "than stated. E2's in-sample back-test found the same (95-98% inside): the ratings "
        "lean towards the bookmakers' view, which is less extreme than final tables. With a "
        "fifth of fixtures hidden, the situation scenarios are in, the ranges and chances "
        "are much closer to right.", "",
        "## 4. Knock-on: 2008/09 to 2025/26 with each run's own promotions and relegations", "",
        "Fully simulated from the real 2008/09 divisions. Clubs in a division they were not "
        "really in keep their real-season rating (no adjustment, Mus's decision on E2-06).", "",
        "Division sizes: every run has the real number of clubs in every division and season"
        + (", except where a late leaver's vacancy follows the club:" if len(sz) else "."), "",
        (_md(sz, {"runs_not_real_size": "{:.1%}"}) if len(sz) else ""), "",
        "Share of real club-seasons spent in the club's real division:", "",
        _md(share, {"share_in_real_division": "{:.1%}"}), "",
        "Clubs promoted into the PL (any club that was in the Championship the season before):", "",
        _md(ko, {"club_seasons_per_run": "{:.1f}", "avg_pts": "{:.1f}", "stayed_up": "{:.1%}"}), "",
        "The second row of each variant is the cross-division case: a club the run promoted "
        "but reality did not, playing the PL on its real Championship-season rating. Clubs "
        "really promoted are the closest real comparison, though not the same clubs. The "
        "step-up penalty and money boost are in strength units (attack + defence), split "
        "equally between attack and defence; the step-up penalty is per division above the "
        "club's real one, the money boost applies only to clubs promoted in the run but not "
        "in reality. Both are off by default.", "",
    ]
    (ROOT / "docs" / "e3_validation.md").write_text("\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10_000)
    main(ap.parse_args().runs)
