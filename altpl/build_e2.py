"""Stage E2 pipeline: tune and fit the ratings model, run the back-tests, write outputs.

    python -m altpl.build_e2            # everything (about 25 minutes on 4 cores)
    python -m altpl.build_e2 --skip-tuning  # reuse the saved tuning grid
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from altpl import backtest as B
from altpl.config import PROCESSED, ROOT, SEASONS, season_label
from altpl.ratings import fit, load_matches

SIGMAS = [0.06, 0.1, 0.15, 0.25, 0.4]
OMEGAS = [0.0, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]
OMEGA0 = 4.0  # odds weight used while choosing sigma
TOL = 0.0005  # log-loss tolerance when choosing settings (see choose)

_M: pd.DataFrame | None = None


def _init(m):
    global _M
    _M = m


def _preseason(cfg):
    s, o, season = cfg
    return s, o, season, B.preseason_predictions(_M, season, s, o)


def _holdout(cfg):
    s, o = cfg
    p = B.holdout_predictions(_M, s, o)
    return s, o, p


def _season(args):
    kind, season, s, o, runs = args
    full = fit(_M, s, o) if kind == "insample" else None
    return B.season_test(_M, kind, season, s, o, runs, full=full)


def tune(m, pool):
    """Two steps. sigma (how far a club's ratings move between seasons) is chosen by
    how well last season's ratings predict the next season's matches, at a middling
    odds weight. omega (the odds weight) is then chosen by held-out matches within
    the season, which is how the ratings are used in a scenario."""
    rows = []
    jobs = [(s, OMEGA0, season) for s in SIGMAS for season in SEASONS if season >= 2010]
    out = {}
    for s, o, season, p in pool.map(_preseason, jobs):
        out.setdefault(s, {})[season] = p
    for s, d in out.items():
        idx = m.index[m.season.isin(list(d))]
        p = np.vstack([d[k] for k in sorted(d)])
        rows.append({"step": "pre-season", "sigma": s, "omega": OMEGA0,
                     **B.match_metrics(p, m.loc[idx])})
    pre = pd.DataFrame(rows)
    sigma = float(pre.sort_values("log_loss").sigma.iloc[0])
    preds = {}
    for s, o, p in pool.map(_holdout, [(sigma, o) for o in OMEGAS]):
        met = B.match_metrics(p[["pH", "pD", "pA"]].values, m)
        met["score_log_loss"] = -np.log(p.p_score.clip(1e-12)).mean()
        rows.append({"step": "held-out", "sigma": s, "omega": o, **met})
        preds[(s, o)] = p
    return pd.DataFrame(rows), preds


def division_levels(r, m) -> pd.DataFrame:
    """Average ratings per division-season and the gap to the division above, with
    the number of clubs linking the two (clubs that moved between them)."""
    t = r.teams[r.teams.n > 0]
    lv = t.groupby(["season", "tier"]).agg(clubs=("club_id", "size"), att=("att", "mean"),
                                           defence=("def", "mean"),
                                           strength=("strength", "mean")).reset_index()
    lv["gap_to_tier_above"] = lv.set_index(["season", "tier"]).strength.reindex(
        list(zip(lv.season, lv.tier - 1))).values - lv.strength
    # Expected goals for an average club of this tier against an average club of the
    # tier above, at a neutral ground, as a plain-language reading of the gap.
    above = lv.set_index(["season", "tier"])
    rows = []
    for x in lv.itertuples():
        if (x.season, x.tier - 1) in above.index:
            u = above.loc[(x.season, x.tier - 1)]
            rows.append((np.exp(r.mu + x.att - u.defence), np.exp(r.mu + u.att - x.defence)))
        else:
            rows.append((np.nan, np.nan))
    lv["xg_for_v_tier_above"], lv["xg_against_v_tier_above"] = np.array(rows).T
    moves = t.sort_values(["club_id", "season"]).assign(
        prev_tier=lambda d: d.groupby("club_id").tier.shift(),
        prev_season=lambda d: d.groupby("club_id").season.shift())
    moves = moves[(moves.prev_season == moves.season - 1) & (moves.prev_tier != moves.tier)]
    link = moves.assign(boundary=np.maximum(moves.tier, moves.prev_tier)).groupby(
        ["season", "boundary"]).size()
    lv["movers_from_or_to_tier_above"] = [link.get((s, t), 0) for s, t in zip(lv.season, lv.tier)]
    lv.loc[lv.tier == 1, "movers_from_or_to_tier_above"] = np.nan
    return lv


def choose(tuning: pd.DataFrame, tol: float = TOL) -> tuple[float, float]:
    """sigma: best pre-season log-loss. omega: the least odds weight whose held-out
    log-loss is within ``tol`` of the best; past that, extra weight buys nothing."""
    ho = tuning[tuning.step == "held-out"]
    ok = ho[ho.log_loss <= ho.log_loss.min() + tol]
    best = ok.sort_values("omega").iloc[0]
    return float(best.sigma), float(best.omega)


def main(runs: int = 10_000, workers: int = 4, retune: bool = True):
    m = load_matches()
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(m,)) as pool:
        if retune:
            tuning, preds = tune(m, pool)
            tuning.to_csv(PROCESSED / "e2_tuning.csv", index=False)
        else:
            tuning, preds = pd.read_csv(PROCESSED / "e2_tuning.csv"), {}
        sigma, omega = choose(tuning)
        print("chosen sigma", sigma, "omega", omega)
        if (sigma, omega) not in preds:
            preds[(sigma, omega)] = B.holdout_predictions(m, sigma, omega)

        r = fit(m, sigma, omega)
        teams = r.teams.copy()
        teams.insert(1, "season_label", teams.season.map(season_label))
        teams.round(4).to_csv(PROCESSED / "ratings.csv", index=False)
        division_levels(r, m).round(4).to_csv(PROCESSED / "division_levels.csv", index=False)
        params = {"sigma": sigma, "omega": omega, "mu": r.mu, "rho": r.rho,
                  "home_season": {str(k): v for k, v in r.home_season.items()},
                  "home_tier": {str(k): v for k, v in r.home_tier.items()}, **r.info}
        (PROCESSED / "ratings_params.json").write_text(json.dumps(params, indent=2))

        # held-out match predictions at the chosen settings, plus benchmarks
        p = preds[(sigma, omega)]
        ho = m[["season", "tier", "date", "home_id", "away_id", "hg", "ag"]].copy()
        ho[["model_pH", "model_pD", "model_pA", "model_p_score"]] = p.values
        ho[["market_pH", "market_pD", "market_pA"]] = m[["pH", "pD", "pA"]].values
        ho.to_csv(PROCESSED / "e2_holdout_matches.csv", index=False)

        jobs = [(k, s, sigma, omega, runs) for k in ("insample", "midseason", "preseason")
                for s in SEASONS if not (k == "preseason" and s < 2010)]
        seasons = pd.concat(pool.map(_season, jobs), ignore_index=True)
        seasons.round(5).to_csv(PROCESSED / "e2_backtest_seasons.csv", index=False)
    return m, r, tuning, ho, seasons


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10_000)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--skip-tuning", action="store_true",
                    help="reuse data/processed/e2_tuning.csv instead of rerunning the grid")
    a = ap.parse_args()
    main(a.runs, a.workers, retune=not a.skip_tuning)
    from altpl.e2_report import write_report
    write_report()
    print("wrote", ROOT / "docs" / "e2_validation.md")
