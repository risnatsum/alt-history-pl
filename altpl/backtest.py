"""Stage E2 back-tests of the ratings model.

1. Held-out matches (within season): fit with a fifth of each season's matches
   hidden, predict them. This is the job the ratings do in a scenario: rate clubs
   from their real season and predict fixtures that never happened. Used to choose
   sigma and omega.
2. Pre-season: ratings fitted only on earlier seasons predict a whole season.
   Clubs that changed division are predicted on the common scale with no other
   adjustment, which tests the measured gap between divisions.
3. Mid-season: earlier seasons plus the first half of the season are known; the
   rest is simulated with the real first-half results kept.
4. In-sample: each season re-simulated from its own full-season ratings.

Seasons are simulated with a light Monte Carlo (league table, then play-offs) so
that title, promotion, play-off and relegation odds can be checked against what
actually happened. The full season simulator is stage E3.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from altpl.config import PROCESSED, REFERENCE
from altpl.ratings import Ratings, fit, outcome_probs, score_grid

SEED = 20081

# ---------------------------------------------------------------- reference data


def season_rules() -> pd.DataFrame:
    return pd.read_csv(REFERENCE / "seasons.csv", comment="#").set_index(["season", "tier"])


def real_tables() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "tables.csv")


# ---------------------------------------------------------------- sampling


def sample_scores(lam, nu, rho, rng):
    """Draw Dixon-Coles scores exactly: Poisson draws, accepted with probability
    tau / max(tau) (rejection sampling); rejected draws are redrawn."""
    lam, nu = np.broadcast_arrays(np.asarray(lam, float), np.asarray(nu, float))
    shape = lam.shape
    lam, nu = lam.ravel(), nu.ravel()
    x = np.empty(lam.size, int)
    y = np.empty(lam.size, int)
    tmax = np.maximum.reduce([1 - lam * nu * rho, 1 + lam * rho, 1 + nu * rho,
                              np.full_like(lam, 1 - rho)])
    todo = np.arange(lam.size)
    while todo.size:
        a = rng.poisson(lam[todo])
        b = rng.poisson(nu[todo])
        tau = np.ones(todo.size)
        tau[(a == 0) & (b == 0)] = 1 - lam[todo][(a == 0) & (b == 0)] * nu[todo][(a == 0) & (b == 0)] * rho
        tau[(a == 0) & (b == 1)] = 1 + lam[todo][(a == 0) & (b == 1)] * rho
        tau[(a == 1) & (b == 0)] = 1 + nu[todo][(a == 1) & (b == 0)] * rho
        tau[(a == 1) & (b == 1)] = 1 - rho
        ok = rng.random(todo.size) * tmax[todo] <= tau
        x[todo[ok]], y[todo[ok]] = a[ok], b[ok]
        todo = todo[~ok]
    return x.reshape(shape), y.reshape(shape)


def _winner_two_legs(r, season, tier, A, D, hi, lo, rng):
    """Two-legged tie, higher seed ``hi`` at home in the second leg. A level aggregate
    goes to a coin flip standing in for extra time and penalties."""
    ha = r.home_adv(season, tier)
    rows = np.arange(len(hi))
    l1h, l1a = sample_scores(np.exp(r.mu + ha + A[rows, lo] - D[rows, hi]),
                             np.exp(r.mu + A[rows, hi] - D[rows, lo]), r.rho, rng)
    l2h, l2a = sample_scores(np.exp(r.mu + ha + A[rows, hi] - D[rows, lo]),
                             np.exp(r.mu + A[rows, lo] - D[rows, hi]), r.rho, rng)
    agg_hi = l1a + l2h
    agg_lo = l1h + l2a
    coin = rng.random(len(hi)) < 0.5
    return np.where(agg_hi > agg_lo, hi, np.where(agg_lo > agg_hi, lo, np.where(coin, hi, lo)))


def _winner_one_leg(r, season, tier, A, D, home, away, rng, neutral=False):
    ha = 0.0 if neutral else r.home_adv(season, tier)
    rows = np.arange(len(home))
    g1, g2 = sample_scores(np.exp(r.mu + ha + A[rows, home] - D[rows, away]),
                           np.exp(r.mu + A[rows, away] - D[rows, home]), r.rho, rng)
    coin = rng.random(len(home)) < 0.5
    return np.where(g1 > g2, home, np.where(g2 > g1, away, np.where(coin, home, away)))


def playoff_winner(r, season, tier, rule, order, A, D, rng):
    """Club index promoted through the play-offs in each run. ``order[:, k]`` is the
    club finishing in position k+1."""
    f, t = int(rule.playoff_from), int(rule.playoff_to)
    seed = lambda p: order[:, p - 1]  # noqa: E731
    fmt = str(rule.playoff_format)
    if fmt.startswith("eliminators"):
        # 4v7 and 5v6 one leg at the higher seed; 2nd plays the lower-placed winner,
        # 3rd the other, one leg at home; one-off final on neutral ground.
        e1 = _winner_one_leg(r, season, tier, A, D, seed(f + 2), seed(t), rng)
        e2 = _winner_one_leg(r, season, tier, A, D, seed(f + 3), seed(t - 1), rng)
        rank = np.argsort(order, axis=1)
        rows = np.arange(len(order))
        e1_lower = rank[rows, e1] > rank[rows, e2]
        low, high = np.where(e1_lower, e1, e2), np.where(e1_lower, e2, e1)
        s1 = _winner_one_leg(r, season, tier, A, D, seed(f), low, rng)
        s2 = _winner_one_leg(r, season, tier, A, D, seed(f + 1), high, rng)
    else:
        # two-legged semis: best v worst, second-best v second-worst
        s1 = _winner_two_legs(r, season, tier, A, D, seed(f), seed(t), rng)
        s2 = _winner_two_legs(r, season, tier, A, D, seed(f + 1), seed(t - 1), rng)
    return _winner_one_leg(r, season, tier, A, D, s1, s2, rng, neutral=True)


def simulate(r: Ratings, season: int, tier: int, clubs: list, prior: pd.DataFrame,
             fixtures: pd.DataFrame, deductions: dict, rule, runs: int, rng) -> pd.DataFrame:
    """Monte Carlo of one division-season. ``prior`` has att, def, att_sd, def_sd per
    club (index club_id); each run draws the club's ratings from it. Fixtures with
    a known score (hg/ag not null) are kept as played."""
    n = len(clubs)
    ci = {c: i for i, c in enumerate(clubs)}
    p = prior.loc[clubs]
    A = p.att.values + p.att_sd.values * rng.standard_normal((runs, n))
    D = p["def"].values + p.def_sd.values * rng.standard_normal((runs, n))
    h = fixtures.home_id.map(ci).values
    a = fixtures.away_id.map(ci).values
    known = fixtures.hg.notna().values
    hg = np.empty((runs, len(fixtures)), int)
    ag = np.empty_like(hg)
    hg[:, known] = fixtures.hg.values[known].astype(int)
    ag[:, known] = fixtures.ag.values[known].astype(int)
    u = ~known
    if u.any():
        ha = r.home_adv(season, tier)
        lam = np.exp(r.mu + ha + A[:, h[u]] - D[:, a[u]])
        nu = np.exp(r.mu + A[:, a[u]] - D[:, h[u]])
        hg[:, u], ag[:, u] = sample_scores(lam, nu, r.rho, rng)
    hp = np.where(hg > ag, 3, np.where(hg == ag, 1, 0))
    ap = np.where(ag > hg, 3, np.where(hg == ag, 1, 0))
    off = (np.arange(runs) * n)[:, None]
    tot = runs * n
    pts = (np.bincount((off + h).ravel(), hp.ravel(), tot) +
           np.bincount((off + a).ravel(), ap.ravel(), tot)).reshape(runs, n)
    gf = (np.bincount((off + h).ravel(), hg.ravel(), tot) +
          np.bincount((off + a).ravel(), ag.ravel(), tot)).reshape(runs, n)
    ga = (np.bincount((off + h).ravel(), ag.ravel(), tot) +
          np.bincount((off + a).ravel(), hg.ravel(), tot)).reshape(runs, n)
    pts = pts - np.array([deductions.get(c, 0) for c in clubs])
    key = pts * 1e6 + (gf - ga + 500) * 1e3 + gf + rng.random((runs, n))
    order = np.argsort(-key, axis=1)
    pos = np.argsort(order, axis=1) + 1
    out = pd.DataFrame({"season": season, "tier": tier, "club_id": clubs,
                        "xpts": pts.mean(0), "pts_p05": np.percentile(pts, 5, axis=0),
                        "pts_p95": np.percentile(pts, 95, axis=0), "xpos": pos.mean(0),
                        "p_title": (pos == 1).mean(0)})
    out["p_auto"] = (pos <= rule.auto_up).mean(0)
    out["p_playoff"] = ((pos >= rule.playoff_from) & (pos <= rule.playoff_to)).mean(0) \
        if rule.playoff_up else 0.0
    out["p_releg"] = (pos > rule.teams - rule.relegated).mean(0) if rule.relegated else 0.0
    if rule.playoff_up:
        win = playoff_winner(r, season, tier, rule, order, A, D, rng)
        out["p_promoted"] = out.p_auto + np.bincount(win, minlength=n) / runs
    else:
        out["p_promoted"] = 0.0
    return out


# ---------------------------------------------------------------- rating priors


def prior_from_fit(r: Ratings, season: int, clubs: list) -> pd.DataFrame:
    """Each club's ratings for ``season`` with their uncertainty. A club with no
    rating for that season carries its latest rating forward, its uncertainty widened
    by sigma per season; a club never seen before gets the average first-season
    rating of earlier newcomers and their spread."""
    t = r.teams
    first = t.groupby("club_id").season.transform("min")
    new = t[(first == t.season) & (t.season > t.season.min())]
    rows = []
    for c in clubs:
        tc = t[(t.club_id == c) & (t.season <= season)]
        if len(tc) and tc.season.max() == season and tc.n.iloc[-1] > 0:
            x = tc.iloc[-1]
            rows.append((c, x.att, x["def"], x.att_sd, x.def_sd))
        elif len(tc):
            x = tc[tc.n > 0].iloc[-1] if (tc.n > 0).any() else tc.iloc[-1]
            k = season - x.season
            rows.append((c, x.att, x["def"], np.hypot(x.att_sd, r.sigma * np.sqrt(k)),
                         np.hypot(x.def_sd, r.sigma * np.sqrt(k))))
        else:
            rows.append((c, new.att.mean(), new["def"].mean(), new.att.std(), new["def"].std()))
    return pd.DataFrame(rows, columns=["club_id", "att", "def", "att_sd", "def_sd"]).set_index("club_id")


# ---------------------------------------------------------------- 1. held-out matches


def holdout_predictions(m: pd.DataFrame, sigma: float, omega: float, folds: int = 5,
                        seed: int = SEED) -> pd.DataFrame:
    """Out-of-sample 1X2 probabilities and exact-score probability for every match."""
    rng = np.random.default_rng(seed)
    fold = rng.integers(0, folds, len(m))
    out = np.empty((len(m), 4))
    for k in range(folds):
        test = fold == k
        r = fit(m, sigma=sigma, omega=omega, weight=(~test).astype(float))
        lk = r.lookup()
        ha = np.array([r.home_adv(s, t) for s, t in zip(m.season[test], m.tier[test])])
        h = np.array([lk[(s, c)] for s, c in zip(m.season[test], m.home_id[test])])
        a = np.array([lk[(s, c)] for s, c in zip(m.season[test], m.away_id[test])])
        lam = np.exp(r.mu + ha + h[:, 0] - a[:, 1])
        nu = np.exp(r.mu + a[:, 0] - h[:, 1])
        out[test, :3] = outcome_probs(lam, nu, r.rho)
        g = score_grid(lam, nu, r.rho)
        hg = np.minimum(m.hg.values[test], 10)
        ag = np.minimum(m.ag.values[test], 10)
        out[test, 3] = g[np.arange(test.sum()), hg, ag]
    return pd.DataFrame(out, columns=["pH", "pD", "pA", "p_score"], index=m.index)


def preseason_predictions(m: pd.DataFrame, season: int, sigma: float, omega: float) -> np.ndarray:
    """1X2 probabilities for every match of ``season`` from ratings fitted on earlier
    seasons only (each club at its latest rating; newcomers at the newcomer average)."""
    r = fit(m[m.season < season].reset_index(drop=True), sigma=sigma, omega=omega)
    cur = m[m.season == season]
    clubs = sorted(set(cur.home_id) | set(cur.away_id))
    pr = prior_from_fit(r, season, clubs)
    ha = np.array([r.home_adv(season, t) for t in cur.tier])
    h, a = pr.loc[cur.home_id], pr.loc[cur.away_id]
    lam = np.exp(r.mu + ha + h.att.values - a["def"].values)
    nu = np.exp(r.mu + a.att.values - h["def"].values)
    return outcome_probs(lam, nu, r.rho)


def match_metrics(p: np.ndarray, m: pd.DataFrame) -> dict:
    res = np.select([m.hg > m.ag, m.hg == m.ag], [0, 1], 2)
    onehot = np.eye(3)[res]
    pr = np.clip(p[np.arange(len(m)), res], 1e-12, 1)
    return {"matches": len(m), "log_loss": -np.log(pr).mean(),
            "brier": ((p - onehot) ** 2).sum(1).mean(),
            "accuracy": (p.argmax(1) == res).mean()}


def base_rates(m: pd.DataFrame) -> np.ndarray:
    """Home/draw/away frequencies by tier: the no-skill benchmark."""
    res = np.select([m.hg > m.ag, m.hg == m.ag], [0, 1], 2)
    f = pd.DataFrame(np.eye(3)[res], index=m.index).groupby(m.tier).transform("mean")
    return f.values


def calibration_bins(p: np.ndarray, hit: np.ndarray, edges=(0, .05, .1, .2, .3, .4, .5, .6,
                                                            .7, .8, .9, .95, 1.0001)):
    b = pd.cut(p, edges, right=False)
    g = pd.DataFrame({"p": p, "hit": hit, "bin": b}).groupby("bin", observed=True)
    return g.agg(n=("p", "size"), predicted=("p", "mean"), observed=("hit", "mean")).reset_index()


# ---------------------------------------------------------------- 2-4. season tests


def _division_inputs(m, tables, season, tier):
    clubs = tables[(tables.season == season) & (tables.tier == tier)]
    fx = m[(m.season == season) & (m.tier == tier)]
    ded = dict(zip(clubs.club_id, clubs.deduction))
    return clubs, fx, ded


def season_test(m: pd.DataFrame, kind: str, season: int, sigma: float, omega: float,
                runs: int, full: Ratings | None = None, seed: int = SEED) -> pd.DataFrame:
    """Simulate every division of ``season`` under one information set:
    'preseason' (earlier seasons only), 'midseason' (plus the first half of the
    season, by date) or 'insample' (the full-season ratings ``full``)."""
    tables = real_tables()
    rules = season_rules()
    rng = np.random.default_rng([seed, season, ["preseason", "midseason", "insample"].index(kind)])
    if kind == "insample":
        r = full
        known_mask = pd.Series(False, index=m.index)
    else:
        if kind == "preseason":
            train = m[m.season < season]
            known_mask = pd.Series(False, index=m.index)
        else:
            cur = m[m.season == season]
            mid = cur.groupby("tier").date.transform("median")
            known_mask = pd.Series(False, index=m.index)
            known_mask[cur.index] = (cur.date <= mid).values
            train = m[(m.season < season) | known_mask]
        memb = tables[tables.season == season][["season", "tier", "club_id"]] \
            if kind == "midseason" else None
        r = fit(train.reset_index(drop=True), sigma=sigma, omega=omega, membership=memb)
    out = []
    for tier in range(1, 6):
        rule = rules.loc[(season, tier)]
        if rule.ranking == "ppg":
            continue  # curtailed 2019/20 divisions were decided on points per game
        clubs, fx, ded = _division_inputs(m, tables, season, tier)
        fx = fx[["home_id", "away_id"]].assign(
            hg=m.hg[fx.index].where(known_mask[fx.index]),
            ag=m.ag[fx.index].where(known_mask[fx.index]))
        prior = prior_from_fit(r, season, list(clubs.club_id))
        sim = simulate(r, season, tier, list(clubs.club_id), prior, fx, ded, rule, runs, rng)
        real = clubs.set_index("club_id")
        sim["pts"] = sim.club_id.map(real.pts)
        sim["pos"] = sim.club_id.map(real.pos)
        sim["title"] = sim.pos == 1
        sim["auto"] = sim.pos <= rule.auto_up
        sim["playoff"] = (sim.pos >= rule.playoff_from) & (sim.pos <= rule.playoff_to) & \
            (rule.playoff_up > 0)
        sim["releg_zone"] = sim.pos > rule.teams - rule.relegated
        sim["promoted"] = sim.club_id.map(real.outcome).fillna("").str.startswith("promoted")
        out.append(sim)
    res = pd.concat(out, ignore_index=True)
    res["kind"] = kind
    return res
