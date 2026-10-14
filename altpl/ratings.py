"""Stage E2 ratings model: Dixon-Coles attack/defence ratings per club-season, one scale.

For a match in season s and tier t, home club h, away club a:

    log(home expected goals) = mu + home_season[s] + home_tier[t] + att[h,s] - def[a,s]
    log(away expected goals) = mu + att[a,s] - def[h,s]

Scores are independent Poissons with the Dixon-Coles correction for 0-0, 1-0, 0-1 and
1-1 (parameter rho). Every club-season has its own attack and defence rating.

Divisions never meet inside a season, so on their own each division's ratings would
float. They are tied to one scale by linking each club's rating to its rating in its
previous season in the data (a random walk with standard deviation ``sigma`` per
season). A club that changes division carries its strength across, so the clubs that
move between two divisions fix the gap between them. Because mu is shared by every
tier, a rating means the same thing in any division: a Championship club rated 0.3
would be expected to score and concede in the Premier League as a 0.3 PL club does.

Bookmaker odds sharpen the ratings. Each match's 1X2 and over/under 2.5 goals prices
are converted into the expected goals they imply; these enter the likelihood as
extra, fractional "goals" with weight ``omega`` (omega = 1 counts the market's view
of a match as much as its actual score).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

from altpl.clubs import club_id
from altpl.config import PROCESSED, SOURCES

KEY = ["season", "tier", "home_id", "away_id"]
MAXG = 10  # score grid 0..MAXG goals per side


# ---------------------------------------------------------------- bookmaker odds

def devig(odds: np.ndarray) -> np.ndarray:
    """Remove the bookmaker margin by the power method: p_i = (1/o_i)^k with k set so
    the probabilities sum to 1. Unlike scaling every price by the same factor, this
    takes more margin off long shots than favourites, which removes the
    favourite-longshot bias in these odds (see docs/e2_validation.md)."""
    inv = 1 / np.asarray(odds, float)
    k = np.ones(len(inv))
    for _ in range(30):
        q = inv ** k[:, None]
        k -= (q.sum(1) - 1) / (np.log(inv) * q).sum(1)
    return inv ** k[:, None]


def market_odds() -> pd.DataFrame:
    """Margin-free market probabilities per match: home, draw, away, over 2.5 goals.

    Average odds across bookmakers (football-data's Avg columns, or BbAv in older
    files, standardised as Avg*) are used; Bet365 fills any gap, then the
    football-data GitHub mirror (2013/14 Premier League).
    """
    fd = pd.read_csv(SOURCES / "footballdata.csv", low_memory=False)
    avg = fd[["AvgH", "AvgD", "AvgA"]].notna().all(axis=1)
    h = fd.AvgH.where(avg, fd.B365H)
    d = fd.AvgD.where(avg, fd.B365D)
    a = fd.AvgA.where(avg, fd.B365A)
    o = pd.DataFrame({"season": fd.season, "tier": fd.tier, "home": fd.home, "away": fd.away,
                      "h": h, "d": d, "a": a, "o25": fd.AvgO25, "u25": fd.AvgU25})
    mir = pd.read_csv(SOURCES / "footballdata_mirror.csv", low_memory=False)
    mir = pd.DataFrame({"season": mir.season, "tier": mir.tier, "home": mir.home, "away": mir.away,
                        "h": mir.OddHome, "d": mir.OddDraw, "a": mir.OddAway,
                        "o25": mir.Over25, "u25": mir.Under25})
    out = []
    for src in (o, mir):
        src = src.dropna(subset=["h", "d", "a"]).copy()
        src = src[(src[["h", "d", "a"]] > 1).all(axis=1)]
        src["home_id"] = [club_id(n, s) for n, s in zip(src.home, src.season)]
        src["away_id"] = [club_id(n, s) for n, s in zip(src.away, src.season)]
        src["pH"], src["pD"], src["pA"] = devig(src[["h", "d", "a"]].values).T
        ok = (src.o25 > 1) & (src.u25 > 1)
        src["pO25"] = np.nan
        src.loc[ok, "pO25"] = devig(src.loc[ok, ["o25", "u25"]].values)[:, 0]
        out.append(src[KEY + ["pH", "pD", "pA", "pO25"]])
    allo = pd.concat(out).drop_duplicates(KEY, keep="first")
    return allo


def implied_goals(pH, pA, pO25, iters=40):
    """Expected home and away goals that reproduce the market's home-win, away-win and
    over-2.5 probabilities under independent Poissons (least squares, Gauss-Newton).
    Where over/under prices are missing, only the 1X2 probabilities are matched."""
    n = len(pH)
    x = np.full((n, 2), np.log(1.35))
    x[:, 1] = np.log(1.1)
    tgt = np.column_stack([pH, pA, np.nan_to_num(pO25, nan=0.0)])
    use = np.column_stack([np.ones(n), np.ones(n), ~np.isnan(pO25)]).astype(float)

    def f(x):
        lam, nu = np.exp(x[:, 0]), np.exp(x[:, 1])
        g = np.arange(MAXG + 1)
        ph = poisson.pmf(g[None, :], lam[:, None])
        pa = poisson.pmf(g[None, :], nu[:, None])
        joint = ph[:, :, None] * pa[:, None, :]
        home = np.tril(np.ones((MAXG + 1, MAXG + 1)), -1)
        pHm = (joint * home).sum((1, 2))
        pAm = (joint * home.T).sum((1, 2))
        pO = 1 - poisson.cdf(2, lam + nu)
        return (np.column_stack([pHm, pAm, pO]) - tgt) * use

    for _ in range(iters):
        r = f(x)
        J = np.empty((n, 3, 2))
        for k in range(2):
            dx = np.zeros_like(x)
            dx[:, k] = 1e-5
            J[:, :, k] = (f(x + dx) - r) / 1e-5
        JTJ = np.einsum("nik,nil->nkl", J, J) + 1e-9 * np.eye(2)
        step = np.linalg.solve(JTJ, np.einsum("nik,ni->nk", J, r)[..., None])[..., 0]
        x -= np.clip(step, -0.5, 0.5)
    return np.exp(x[:, 0]), np.exp(x[:, 1])


def load_matches() -> pd.DataFrame:
    """Every real league match (awarded results excluded) with market-implied goals."""
    res = pd.read_csv(PROCESSED / "results.csv")
    res = res[~res.awarded.astype(bool)].copy()
    odds = market_odds()
    m = res.merge(odds, on=KEY, how="left")
    has = m.pH.notna().values
    xh = np.full(len(m), np.nan)
    xa = np.full(len(m), np.nan)
    xh[has], xa[has] = implied_goals(m.pH.values[has], m.pA.values[has], m.pO25.values[has])
    m["xh"], m["xa"] = xh, xa
    m["date"] = pd.to_datetime(m.date)
    return m.sort_values(["season", "tier", "date", "home_id"]).reset_index(drop=True)


# ---------------------------------------------------------------- the model

@dataclass
class Ratings:
    teams: pd.DataFrame          # season, tier, club_id, att, def, att_sd, def_sd, n
    mu: float
    rho: float
    home_season: dict
    home_tier: dict
    sigma: float
    omega: float
    info: dict = field(default_factory=dict)

    def lookup(self):
        return {(r.season, r.club_id): (r.att, r.def_) for r in
                self.teams.rename(columns={"def": "def_"}).itertuples()}

    def home_adv(self, season, tier):
        return self.home_season.get(season, np.mean(list(self.home_season.values()))) + \
            self.home_tier.get(tier, 0.0)


def _dc_tau_terms(x, y, lam, nu, rho):
    """log tau and its derivatives w.r.t. log lam, log nu and rho."""
    tau = np.ones_like(lam)
    dh = np.zeros_like(lam)
    da = np.zeros_like(lam)
    dr = np.zeros_like(lam)
    m00 = (x == 0) & (y == 0)
    m01 = (x == 0) & (y == 1)
    m10 = (x == 1) & (y == 0)
    m11 = (x == 1) & (y == 1)
    tau[m00] = 1 - lam[m00] * nu[m00] * rho
    tau[m01] = 1 + lam[m01] * rho
    tau[m10] = 1 + nu[m10] * rho
    tau[m11] = 1 - rho
    tau = np.maximum(tau, 1e-10)
    dh[m00] = -lam[m00] * nu[m00] * rho / tau[m00]
    da[m00] = dh[m00]
    dh[m01] = lam[m01] * rho / tau[m01]
    da[m10] = nu[m10] * rho / tau[m10]
    dr[m00] = -lam[m00] * nu[m00] / tau[m00]
    dr[m01] = lam[m01] / tau[m01]
    dr[m10] = nu[m10] / tau[m10]
    dr[m11] = -1 / tau[m11]
    return np.log(tau), dh, da, dr


def fit(m: pd.DataFrame, sigma: float = 0.15, omega: float = 1.0,
        weight: np.ndarray | None = None, ridge: float = 1e-4,
        membership: pd.DataFrame | None = None) -> Ratings:
    """Fit ratings to matches ``m``. ``weight`` (0/1 per match) holds matches out:
    a held-out match neither counts as a result nor contributes its odds, but its
    clubs still get a rating for that season (from their other matches, or from
    their neighbouring seasons alone)."""
    w = np.ones(len(m)) if weight is None else np.asarray(weight, float)
    ts = pd.concat([m[["season", "tier", "home_id"]].rename(columns={"home_id": "club_id"}),
                    m[["season", "tier", "away_id"]].rename(columns={"away_id": "club_id"})])
    if membership is not None:
        ts = pd.concat([ts, membership[["season", "tier", "club_id"]]])
    ts = ts.drop_duplicates(["season", "club_id"]).sort_values(["club_id", "season"])
    ts = ts.reset_index(drop=True)
    T = len(ts)
    idx = {(s, c): i for i, (s, c) in enumerate(zip(ts.season, ts.club_id))}
    hi = np.array([idx[k] for k in zip(m.season, m.home_id)])
    ai = np.array([idx[k] for k in zip(m.season, m.away_id)])
    seasons = sorted(m.season.unique())
    sidx = {s: i for i, s in enumerate(seasons)}
    si = m.season.map(sidx).values
    ti = m.tier.values - 1
    S = len(seasons)

    # random-walk links between a club's consecutive seasons in the data
    prev = ts.groupby("club_id").season.shift()
    li = np.flatnonzero(prev.notna().values)
    lj = li - 1
    lk = (ts.season.values[li] - prev.values[li]).astype(float)
    lw = 1 / (sigma ** 2 * lk)

    x = m.hg.values.astype(float)
    y = m.ag.values.astype(float)
    xh = np.nan_to_num(m.xh.values)
    xa = np.nan_to_num(m.xa.values)
    wo = omega * w * m.xh.notna().values

    o_mu = 2 * T
    o_hs = o_mu + 1
    o_ht = o_hs + S
    o_rho = o_ht + 4
    P = o_rho + 1

    def unpack(th):
        att, dfn = th[:T], th[T:2 * T]
        mu = th[o_mu]
        hs = th[o_hs:o_hs + S]
        ht = np.concatenate([[0.0], th[o_ht:o_ht + 4]])
        return att, dfn, mu, hs, ht, th[o_rho]

    def obj(th):
        att, dfn, mu, hs, ht, rho = unpack(th)
        eh = mu + hs[si] + ht[ti] + att[hi] - dfn[ai]
        ea = mu + att[ai] - dfn[hi]
        lam, nu = np.exp(eh), np.exp(ea)
        lt, dth, dta, dtr = _dc_tau_terms(x, y, lam, nu, rho)
        ll = w * (x * eh - lam + y * ea - nu + lt) + wo * (xh * eh - lam + xa * ea - nu)
        gh = w * (x - lam + dth) + wo * (xh - lam)
        ga = w * (y - nu + dta) + wo * (xa - nu)
        g = np.zeros(P)
        g[:T] = np.bincount(hi, gh, T) + np.bincount(ai, ga, T)
        g[T:2 * T] = -np.bincount(ai, gh, T) - np.bincount(hi, ga, T)
        g[o_mu] = gh.sum() + ga.sum()
        g[o_hs:o_hs + S] = np.bincount(si, gh, S)
        g[o_ht:o_ht + 4] = np.bincount(ti, gh, 5)[1:]
        g[o_rho] = (w * dtr).sum()
        f = -ll.sum()
        g = -g
        for o in (0, T):
            d = th[o + li] - th[o + lj]
            f += 0.5 * (lw * d * d).sum()
            np.add.at(g, o + li, lw * d)
            np.add.at(g, o + lj, -lw * d)
        f += 0.5 * ridge * (th[:2 * T] ** 2).sum()
        g[:2 * T] += ridge * th[:2 * T]
        return f, g

    th0 = np.zeros(P)
    th0[o_mu] = np.log(1.3)
    th0[o_hs:o_hs + S] = 0.25
    bounds = [(None, None)] * (P - 1) + [(-0.3, 0.3)]
    r = minimize(obj, th0, jac=True, method="L-BFGS-B", bounds=bounds,
                 options={"maxiter": 5000, "maxfun": 10000, "ftol": 1e-12, "gtol": 1e-6})
    att, dfn, mu, hs, ht, rho = unpack(r.x)

    # Shift both ratings so the average Premier League club-season has attack 0.
    # Adding the same constant to every attack and defence changes no prediction.
    c = att[ts.tier.values == 1].mean() if (ts.tier == 1).any() else att.mean()
    att, dfn = att - c, dfn - c

    # Approximate standard errors from the diagonal of the information matrix, counting
    # real results and the season links but not the odds: the odds are not independent
    # observations, and counting them at weight omega would make every rating look
    # several times more certain than it is.
    eh = mu + hs[si] + ht[ti] + att[hi] - dfn[ai]
    ea = mu + att[ai] - dfn[hi]
    lam, nu = np.exp(eh), np.exp(ea)
    wt = w
    link_info = np.bincount(li, lw, T) + np.bincount(lj, lw, T)
    i_att = np.bincount(hi, wt * lam, T) + np.bincount(ai, wt * nu, T) + link_info + ridge
    i_def = np.bincount(ai, wt * lam, T) + np.bincount(hi, wt * nu, T) + link_info + ridge
    n = np.bincount(hi, w, T) + np.bincount(ai, w, T)

    teams = ts.assign(att=att, **{"def": dfn}, att_sd=1 / np.sqrt(i_att),
                      def_sd=1 / np.sqrt(i_def), n=n.astype(int))
    teams["strength"] = teams.att + teams["def"]
    return Ratings(teams=teams, mu=float(mu), rho=float(rho),
                   home_season={s: float(hs[i]) for s, i in sidx.items()},
                   home_tier={t + 1: float(ht[t]) for t in range(5)},
                   sigma=sigma, omega=omega,
                   info={"converged": bool(r.success), "nit": int(r.nit), "nll": float(r.fun)})


# ---------------------------------------------------------------- predictions

def score_grid(lam, nu, rho):
    """P(home goals = i, away goals = j) for each match, shape (n, MAXG+1, MAXG+1)."""
    lam, nu = np.atleast_1d(lam), np.atleast_1d(nu)
    g = np.arange(MAXG + 1)
    ph = poisson.pmf(g[None, :], lam[:, None])
    pa = poisson.pmf(g[None, :], nu[:, None])
    p = ph[:, :, None] * pa[:, None, :]
    p[:, 0, 0] *= np.maximum(1 - lam * nu * rho, 0)
    p[:, 0, 1] *= 1 + lam * rho
    p[:, 1, 0] *= 1 + nu * rho
    p[:, 1, 1] *= 1 - rho
    return p / p.sum((1, 2), keepdims=True)


def outcome_probs(lam, nu, rho):
    p = score_grid(lam, nu, rho)
    home = np.tril(np.ones((MAXG + 1, MAXG + 1)), -1)
    return np.column_stack([(p * home).sum((1, 2)), np.trace(p, axis1=1, axis2=2),
                            (p * home.T).sum((1, 2))])


def match_rates(r: Ratings, season, tier, home_att, home_def, away_att, away_def,
                neutral=False):
    ha = 0.0 if neutral else r.home_adv(season, tier)
    lam = np.exp(r.mu + ha + home_att - away_def)
    nu = np.exp(r.mu + away_att - home_def)
    return lam, nu
