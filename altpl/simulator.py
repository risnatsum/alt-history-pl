"""Stage E3 season simulator: Monte Carlo of the whole pyramid, season by season.

One run plays every division of a season, then carries its own promotions and
relegations into the next season, so who is in which division can differ between
runs. Every scenario uses this module; a scenario changes only the ``World`` it is
given (which clubs exist, division sizes, promotion and relegation places), never
the code.

Per season and division, in each run:

1. Every club draws its attack and defence ratings for the season from its E2 rating
   and standard error (``data/processed/ratings.csv``). A club playing a division it
   was not really in keeps its real-season rating: the E2 ratings share one scale
   across divisions (assumptions log E2-02). Optional sensitivities: ``step_up``
   (a penalty for playing above the club's real division) and ``money_boost`` (a
   lift for a club promoted in the run but not in reality). Both are off by default.
2. Fixtures: a double round robin of whoever is in the division, any size (with an
   odd number, every club simply plays 2(n-1) matches; rounds are not modelled). A
   fixture that really happened in that division and season keeps its real score
   ("anchored"); anything else is drawn from the Dixon-Coles model. ``anchored=False``
   simulates every fixture, as a check.
3. Table: points (or points per game in the curtailed 2019/20 divisions), goal
   difference, goals scored, then a random draw. Real deductions follow the club into
   whichever division it is in. Expunged records count for nothing.
4. Play-offs in the season's real format, with extra time and a coin flip for
   penalties. A play-off tie that really happened keeps its real winner; if the whole
   play-off field matches reality, the real play-off winner goes up.
5. Moves: automatic places and play-off winners go up. Relegation then fills each
   division to its size for next season, working down from the top: normally that is
   the season's real number of relegation places; when a club leaves the pyramid
   (expelled, demoted, wound up, or removed by a scenario) the best-placed club in
   the drop zone is reprieved, and if a division is still short the next-best club
   below is promoted (a cascade). The National League's entrants from below are the
   clubs really promoted into it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from altpl.backtest import sample_scores
from altpl.config import FIRST_SEASON, LAST_SEASON, PROCESSED, REFERENCE, SOURCES
from altpl.clubs import club_id

SEED = 20083
TIERS = (1, 2, 3, 4, 5)
BOTTOM = 5  # lowest modelled division; clubs relegated from it leave the model

# outcome codes stored per run, season and club
NONE, AUTO, PLAYOFF, RELEGATED, LEFT, CHAMPION = 0, 1, 2, 3, 4, 5


# ---------------------------------------------------------------- reference data


class Reality:
    """Everything real the simulator needs, loaded once and indexed by club."""

    def __init__(self):
        self.results = pd.read_csv(PROCESSED / "results.csv")
        self.tables = pd.read_csv(PROCESSED / "tables.csv")
        self.membership = pd.read_csv(PROCESSED / "membership.csv")
        self.ratings = pd.read_csv(PROCESSED / "ratings.csv")
        self.params = json.loads((PROCESSED / "ratings_params.json").read_text())
        self.rules = pd.read_csv(REFERENCE / "seasons.csv", comment="#").set_index(["season", "tier"])
        self.adjustments = pd.read_csv(REFERENCE / "adjustments.csv", comment="#")
        self.exceptions = pd.read_csv(REFERENCE / "movement_exceptions.csv", comment="#")

        clubs = sorted(set(self.membership.club_id) | set(self.ratings.club_id))
        self.clubs = clubs
        self.ci = {c: i for i, c in enumerate(clubs)}
        self.seasons = list(range(FIRST_SEASON, self.membership.season.max() + 1))
        C, S = len(clubs), len(self.seasons)

        # real division of every club each season (0 = outside the pyramid)
        self.tier = np.zeros((S, C), np.int8)
        for s, t, c in self.membership[["season", "tier", "club_id"]].itertuples(index=False):
            self.tier[s - FIRST_SEASON, self.ci[c]] = t
        self.sizes = {(s, t): int(n) for (s, t), n in
                      self.membership.groupby(["season", "tier"]).size().items()}

        self._load_ratings()
        self._load_results()
        self._load_playoffs()
        self._load_events()

    # -- ratings: every club gets a rating for every season. A club with no real
    # rating that season (outside the pyramid in reality) carries its nearest real
    # rating, its uncertainty widened by sigma per season of distance (E2-02).
    def use_ratings(self, teams: pd.DataFrame, params: dict) -> None:
        """Swap in another set of ratings (same columns as ratings.csv; params with
        mu, rho, sigma, home_season, home_tier), e.g. ratings fitted with some
        matches held out for a back-test."""
        self.ratings = teams
        self.params = {**params,
                       "home_season": {str(k): v for k, v in params["home_season"].items()},
                       "home_tier": {str(k): v for k, v in params["home_tier"].items()}}
        self._load_ratings()

    def _load_ratings(self):
        S, C = len(self.seasons), len(self.clubs)
        sig = self.params["sigma"]
        att = np.full((S, C), np.nan)
        dfn = np.full((S, C), np.nan)
        asd = np.full((S, C), np.nan)
        dsd = np.full((S, C), np.nan)
        r = self.ratings[self.ratings.n > 0]
        si = r.season.values - FIRST_SEASON
        ci = r.club_id.map(self.ci).values
        att[si, ci], dfn[si, ci] = r.att.values, r["def"].values
        asd[si, ci], dsd[si, ci] = r.att_sd.values, r.def_sd.values
        self.rated = ~np.isnan(att)
        for c in range(C):
            have = np.flatnonzero(self.rated[:, c])
            if not len(have):
                continue
            for s in np.flatnonzero(~self.rated[:, c]):
                j = have[np.argmin(np.abs(have - s) + 0.1 * (have > s))]  # prefer earlier
                k = abs(s - j)
                att[s, c], dfn[s, c] = att[j, c], dfn[j, c]
                asd[s, c] = np.hypot(asd[j, c], sig * np.sqrt(k))
                dsd[s, c] = np.hypot(dsd[j, c], sig * np.sqrt(k))
        self.att, self.dfn, self.asd, self.dsd = att, dfn, asd, dsd
        self.mu, self.rho = self.params["mu"], self.params["rho"]

    def home_adv(self, season, tier):
        hs = self.params["home_season"]
        h = hs.get(str(season), np.mean(list(hs.values())))
        return h + self.params["home_tier"].get(str(tier), 0.0)

    # -- real scores, one CxC grid per season: score and the division it was played in
    def _load_results(self):
        S, C = len(self.seasons), len(self.clubs)
        self.real_hg = np.full((S, C, C), -1, np.int16)
        self.real_ag = np.full((S, C, C), -1, np.int16)
        self.real_div = np.zeros((S, C, C), np.int8)
        r = self.results
        si = r.season.values - FIRST_SEASON
        h = r.home_id.map(self.ci).values
        a = r.away_id.map(self.ci).values
        self.real_hg[si, h, a] = r.hg.values
        self.real_ag[si, h, a] = r.ag.values
        self.real_div[si, h, a] = r.tier.values
        # where each real match was played; unlike real_div this stays put when a
        # back-test hides results
        self.played_div = self.real_div.copy()

    # -- real play-offs: the winner of each whole field (from the E1 tables) and, where
    # engsoccerdata has them, the winner of individual ties.
    def _load_playoffs(self):
        t = self.tables
        self.po_field = {}
        for (s, k), g in t.groupby(["season", "tier"]):
            if (s, k) not in self.rules.index:
                continue
            rule = self.rules.loc[(s, k)]
            if not rule.playoff_up:
                continue
            g = g.set_index("pos")
            seeds = tuple(self.ci[g.loc[p, "club_id"]] for p in
                          range(int(rule.playoff_from), int(rule.playoff_to) + 1))
            win = g[g.outcome == "promoted via play-offs"].club_id
            if len(win) == 1:
                self.po_field[(s, k)] = (seeds, self.ci[win.iloc[0]])
        self.po_ties = {}
        p = pd.read_csv(SOURCES / "engsoccerdata_playoffs.csv")
        div = {"2": 2, "3": 3, "4": 4, "conference": 5}
        p = p[p.division.isin(list(div))]
        for (s, d, rnd), g in p.groupby(["Season", "division", "round"]):
            k = div[d]
            g = g.drop_duplicates(["home", "visitor", "FT"])
            g = g.assign(h=[self.ci[club_id(x, s)] for x in g.home],
                         a=[self.ci[club_id(x, s)] for x in g.visitor])
            g["pair"] = [frozenset(x) for x in zip(g.h, g.a)]
            for pair, gg in g.groupby("pair"):
                x, y = sorted(pair)
                gx = sum(r.hgoal if r.h == x else r.vgoal for r in gg.itertuples())
                gy = sum(r.vgoal if r.h == x else r.hgoal for r in gg.itertuples())
                if gx != gy:
                    w = x if gx > gy else y
                else:  # decided on penalties: the 'pens' column names the winner
                    pw = gg.pens.dropna()
                    if not len(pw):
                        continue
                    w = self.ci[club_id(pw.iloc[-1].split(" ", 1)[1], s)]
                self.po_ties[(s, k, rnd, x, y)] = w

    # -- clubs leaving and entering the pyramid between seasons
    def _load_events(self):
        S = len(self.seasons)
        late = self.exceptions[self.exceptions.vacancy.fillna("") == "unfilled"]
        self.late = {}  # season -> {club: division it would have joined}
        pos = self.tables.set_index(["season", "club_id"]).pos
        for r in late.itertuples():
            # the division it had earned: up if it finished in the automatic places
            up = pos.get((r.season, r.club_id), 99) <= self.rules.loc[(r.season, r.tier)].auto_up
            nxt = r.tier - 1 if up else r.tier + 1 if r.event == "relegated_wound_up" else r.tier
            self.late.setdefault(r.season, {})[self.ci[r.club_id]] = nxt
        self.departures = {}
        self.entrants = {}
        for i in range(S - 1):
            s = self.seasons[i]
            now, nxt = self.tier[i], self.tier[i + 1]
            gone = np.flatnonzero((now > 0) & (nxt == 0))
            normal = {self.ci[c] for c in self.tables[(self.tables.season == s) &
                                                      (self.tables.tier == BOTTOM) &
                                                      (self.tables.outcome == "relegated")].club_id}
            self.departures[s] = sorted(set(gone) - normal)
            self.entrants[s + 1] = sorted(np.flatnonzero((now == 0) & (nxt == BOTTOM)))
        adj = self.adjustments
        ded = adj[adj.type == "deduction"]
        self.deductions = {(s, self.ci[c]): int(p) for s, c, p in
                           zip(ded.season, ded.club_id, ded.points)}
        exp = adj[adj.type == "expunged"]
        self.expunged = {(s, self.ci[c]) for s, c in zip(exp.season, exp.club_id)}


# ---------------------------------------------------------------- the world a run lives in


@dataclass
class World:
    """The rules of one scenario variant. ``real_world`` builds reality; a scenario
    edits a copy. Seasons are start years."""
    start: int
    end: int
    rules: pd.DataFrame                      # (season, tier) -> auto_up, playoff_*, relegated, ranking, playoff_format
    sizes: dict                              # (season, tier) -> clubs in the division
    removed: dict = field(default_factory=dict)       # club_id -> first season it is gone
    removal_fill: str = "cascade"            # "cascade" (best club below goes up) or "reprieve"
    deductions: dict | None = None           # (season, club index) -> points; None = real
    step_up: float = 0.0                     # strength penalty per division above the real one
    money_boost: float = 0.0                 # strength lift for a club promoted in the run only
    name: str = "reality"


def real_world(reality: Reality, start: int = FIRST_SEASON, end: int = LAST_SEASON) -> World:
    return World(start=start, end=end, rules=reality.rules.copy(), sizes=dict(reality.sizes))


# ---------------------------------------------------------------- the simulation result


@dataclass
class Simulation:
    world: World
    clubs: list
    seasons: list
    tier: np.ndarray       # runs x seasons x clubs: division (0 = not in the pyramid)
    pos: np.ndarray        # final position (0 = not in the pyramid)
    pts: np.ndarray        # points after deductions
    played: np.ndarray     # matches counted in the table
    gd: np.ndarray
    outcome: np.ndarray    # NONE / AUTO / PLAYOFF / RELEGATED / LEFT / CHAMPION
    anchored: bool
    seed: int

    @property
    def runs(self):
        return self.tier.shape[0]


# ---------------------------------------------------------------- matches and ties


class _Draws:
    """Per-run ratings for one season: A[run, club], D[run, club]."""

    def __init__(self, A, D, mu, rho):
        self.A, self.D, self.mu, self.rho = A, D, mu, rho

    def rates(self, ha, home, away, rows):
        lam = np.exp(self.mu + ha + self.A[rows, home] - self.D[rows, away])
        nu = np.exp(self.mu + self.A[rows, away] - self.D[rows, home])
        return lam, nu


def _decide(g1, g2, home, away, lam, nu, rng):
    """Winner of a level tie: extra time (a third of a match at the same scoring
    rates), then penalties as a coin flip."""
    win = np.where(g1 > g2, home, np.where(g2 > g1, away, -1))
    lvl = win < 0
    if lvl.any():
        e1 = rng.poisson(lam[lvl] / 3)
        e2 = rng.poisson(nu[lvl] / 3)
        coin = rng.random(lvl.sum()) < 0.5
        win[lvl] = np.where(e1 > e2, home[lvl], np.where(e2 > e1, away[lvl],
                                                         np.where(coin, home[lvl], away[lvl])))
    return win


def _one_leg(dr, ha, home, away, rng, neutral=False):
    rows = np.arange(len(home))
    lam, nu = dr.rates(0.0 if neutral else ha, home, away, rows)
    g1, g2 = sample_scores(lam, nu, dr.rho, rng)
    return _decide(g1, g2, home, away, lam, nu, rng)


def _two_legs(dr, ha, hi, lo, rng):
    """Higher seed ``hi`` at home in the second leg; no away-goals rule (level
    aggregates in the real EFL play-offs went to extra time and penalties, e.g.
    Leicester v Cardiff 2009/10, which Leicester would have won on away goals)."""
    rows = np.arange(len(hi))
    l1, n1 = dr.rates(ha, lo, hi, rows)
    a1, b1 = sample_scores(l1, n1, dr.rho, rng)      # lo home
    l2, n2 = dr.rates(ha, hi, lo, rows)
    a2, b2 = sample_scores(l2, n2, dr.rho, rng)      # hi home
    return _decide(b1 + a2, a1 + b2, hi, lo, l2, n2, rng)


def _tie(reality, season, tier, rnd, dr, ha, home, away, rng, anchored, legs=1, neutral=False):
    """Winner of a play-off tie in every run. ``home`` is the higher seed (or the
    first-named club of a final). A real tie between the same two clubs keeps its
    real winner when ``anchored``."""
    win = (_two_legs(dr, ha, home, away, rng) if legs == 2
           else _one_leg(dr, ha, home, away, rng, neutral))
    if anchored and reality.po_ties:
        lo, hi = np.minimum(home, away), np.maximum(home, away)
        for i in np.unique(lo * 10000 + hi):
            x, y = divmod(int(i), 10000)
            w = reality.po_ties.get((season, tier, rnd, x, y))
            if w is not None:
                win[(lo == x) & (hi == y)] = w
    return win


def _playoffs(reality, season, tier, rule, order, dr, rng, anchored):
    """Club promoted through the play-offs in each run. ``order[:, k]`` is the club
    finishing (k+1)th."""
    f, t = int(rule.playoff_from), int(rule.playoff_to)
    seed = lambda p: order[:, p - 1]  # noqa: E731
    ha = reality.home_adv(season, tier)
    fmt = str(rule.playoff_format)
    if fmt.startswith("eliminators"):
        # National League from 2017/18: 4th v 7th and 5th v 6th, one leg at the higher
        # seed; 2nd hosts the 5th/6th winner and 3rd hosts the 4th/7th winner (fixed
        # bracket, confirmed by the real 2018/19, 2024/25 and 2025/26 ties; see E3-03).
        q1 = _tie(reality, season, tier, "q", dr, ha, seed(f + 2), seed(t), rng, anchored)
        q2 = _tie(reality, season, tier, "q", dr, ha, seed(f + 3), seed(t - 1), rng, anchored)
        s1 = _tie(reality, season, tier, "s", dr, ha, seed(f), q2, rng, anchored)
        s2 = _tie(reality, season, tier, "s", dr, ha, seed(f + 1), q1, rng, anchored)
    else:
        # two-legged semi-finals: best v worst, second-best v second-worst
        s1 = _tie(reality, season, tier, "s", dr, ha, seed(f), seed(t), rng, anchored, legs=2)
        s2 = _tie(reality, season, tier, "s", dr, ha, seed(f + 1), seed(t - 1), rng, anchored, legs=2)
    win = _tie(reality, season, tier, "f", dr, ha, s1, s2, rng, anchored, neutral=True)
    if anchored and (season, tier) in reality.po_field:
        seeds, real_win = reality.po_field[(season, tier)]
        same = np.all(order[:, f - 1:t] == np.array(seeds), axis=1)
        win[same] = real_win
    return win


# ---------------------------------------------------------------- one division-season


def _division(reality, world, season, tier, members, dr, rng, anchored):
    """Play one division in every run. ``members`` is runs x n club indices.
    Returns (order, pts, played, gd, promoted-via-play-offs club per run or None)."""
    runs, n = members.shape
    si = season - FIRST_SEASON
    rule = world.rules.loc[(season, tier)]
    ii, jj = np.where(~np.eye(n, dtype=bool))
    H, Aw = members[:, ii], members[:, jj]
    rhg = reality.real_hg[si][H, Aw]
    real = (rhg >= 0) & (reality.real_div[si][H, Aw] == tier)
    rtier = reality.tier[si]
    realpair = (rtier[H] == tier) & (rtier[Aw] == tier)
    if rule.ranking == "ppg":
        # curtailed season: a real pairing counts only if it was played before the
        # stop; any other pairing counts with the share of fixtures really played
        happened = reality.played_div[si][H, Aw] == tier
        share = happened[realpair].mean() if realpair.any() else 1.0
        played = happened | (~realpair & (rng.random(H.shape) < share))
    else:
        played = np.ones(H.shape, bool)
    exp = np.array([(season, c) in reality.expunged for c in range(len(reality.clubs))])
    played &= ~exp[H] & ~exp[Aw]

    hg = np.zeros(H.shape, np.int32)
    ag = np.zeros(H.shape, np.int32)
    keep = real & played if anchored else np.zeros_like(real)
    hg[keep] = rhg[keep]
    ag[keep] = reality.real_ag[si][H, Aw][keep]
    sim = played & ~keep
    if sim.any():
        r_, c_ = np.nonzero(sim)
        lam, nu = dr.rates(reality.home_adv(season, tier), H[r_, c_], Aw[r_, c_], r_)
        hg[r_, c_], ag[r_, c_] = sample_scores(lam, nu, dr.rho, rng)

    off = (np.arange(runs) * n)[:, None]
    hs = (off + ii[None, :]).ravel()
    as_ = (off + jj[None, :]).ravel()
    w = played.ravel()
    hp = np.where(hg > ag, 3, np.where(hg == ag, 1, 0)).ravel() * w
    ap = np.where(ag > hg, 3, np.where(hg == ag, 1, 0)).ravel() * w
    tot = runs * n
    cnt = lambda x, y: (np.bincount(hs, x, tot) + np.bincount(as_, y, tot)).reshape(runs, n)  # noqa
    pts = cnt(hp, ap)
    gf = cnt(hg.ravel() * w, ag.ravel() * w)
    ga = cnt(ag.ravel() * w, hg.ravel() * w)
    gp = cnt(w.astype(float), w.astype(float))
    ded = world.deductions if world.deductions is not None else reality.deductions
    dv = np.zeros(len(reality.clubs))
    for (ds, c), v in ded.items():
        if ds == season:
            dv[c] = v
    pts = pts - dv[members]
    gd = gf - ga
    expd = exp[members]
    if rule.ranking == "ppg":
        primary = np.round(np.where(gp > 0, pts / np.maximum(gp, 1), 0) * 1e6)
    else:
        primary = pts
    keys = (rng.random((runs, n)), -gf, -gd, -pts, -primary, expd)
    o = np.lexsort(keys, axis=1)
    order = np.take_along_axis(members, o, axis=1)
    pts_o = np.take_along_axis(pts, o, axis=1)
    gp_o = np.take_along_axis(gp, o, axis=1)
    gd_o = np.take_along_axis(gd, o, axis=1)
    po = _playoffs(reality, season, tier, rule, order, dr, rng, anchored) \
        if rule.playoff_up else None
    return order, pts_o, gp_o, gd_o, po


# ---------------------------------------------------------------- season to season


def _transition(reality, world, season, standings, departures, late, entrants, ghosts=()):
    """Membership of every division next season for one run.

    ``standings[tier]`` = (clubs in finishing order, play-off winner or None).
    ``departures`` leave before the balancing, so their division relegates fewer
    (reprieves, as in reality). ``late`` leavers {club: division earned} keep their
    place in the balancing and leave afterwards, so that division runs one short.
    ``ghosts`` (clubs a scenario removes, filled by cascade) also keep their place in
    the balancing; each place they leave is filled by the best club not promoted from
    the division below, and so on down to the National League, which relegates one
    fewer. Returns ({tier: [clubs]}, {club: outcome code}).
    """
    nxt = season + 1
    rules = world.rules
    outcome = {}
    gone = set(departures)
    ghosts = set(ghosts)
    # promoted from each division: automatic places, then the play-off winner
    up = {}
    for k in TIERS:
        order, po = standings[k]
        rule = rules.loc[(season, k)]
        u = [c for c in order[:int(rule.auto_up)]] if k > 1 else []
        for c in u:
            outcome[c] = AUTO
        if po is not None and k > 1:
            u.append(po)
            outcome[po] = PLAYOFF
        up[k] = u
    inside = {c for k in standings for c in standings[k][0]}
    up[BOTTOM + 1] = [c for c in entrants if c not in inside]
    target = {k: world.sizes[(nxt, k)] + sum(1 for t in late.values() if t == k) for k in TIERS}

    def promote_extra(k, n):
        """The next ``n`` best clubs of division k not already going up."""
        if n <= 0 or k > BOTTOM:
            return []
        extra = [c for c in standings[k][0] if c not in up[k] and c not in gone
                 and c not in ghosts][:n]
        for c in extra:
            outcome[c] = AUTO
        up[k] = up[k] + extra
        return extra

    new = {}
    down_prev = []
    cascade = 0  # places in this division taken by the division above's cascade
    for k in TIERS:
        promote_extra(k + 1, cascade) if k < BOTTOM else None
        order = standings[k][0]
        stay = [c for c in order if c not in up[k] and c not in gone]
        incoming = [c for c in up.get(k + 1, []) if c not in gone] + down_prev
        pool = stay + incoming
        excess = len(pool) - target[k]
        down = []
        if excess > 0:
            cand = [c for c in stay if c not in incoming]
            down = cand[len(cand) - excess:]
        elif excess < 0:
            # still short: promote the next-best clubs from the division below
            if k == BOTTOM:
                raise ValueError(f"{nxt}: National League {-excess} club(s) short")
            pool = pool + promote_extra(k + 1, -excess)
        for c in down:
            outcome[c] = RELEGATED
        new[k] = [c for c in pool if c not in down]
        here = [c for c in new[k] if c in ghosts]
        if here:
            new[k] = [c for c in new[k] if c not in ghosts]
            if k < BOTTOM:
                new[k] += promote_extra(k + 1, len(here))
            else:  # nothing below the National League: reprieve instead
                back = down[:len(here)]
                new[k] += back
                down = down[len(back):]
                for c in back:
                    outcome[c] = NONE
        # the division below is now short by every club the cascade took from it;
        # the next iteration fills those places from the division below that
        cascade += len(here)
        down_prev = down
    for c in departures:
        outcome[c] = LEFT
    for c in ghosts:
        outcome[c] = LEFT
    real_late = set(late)
    for k in TIERS:
        for c in [c for c in new[k] if c in real_late]:
            new[k].remove(c)
            outcome[c] = LEFT
    return new, outcome


def _real_standings(reality, world, season):
    """The real final standings of ``season`` with the real play-off winners."""
    st = {}
    t = reality.tables[reality.tables.season == season]
    for k in TIERS:
        g = t[t.tier == k].sort_values("pos")
        order = [reality.ci[c] for c in g.club_id]
        # expunged clubs have no table row; they finish bottom
        si = season - FIRST_SEASON
        extra = [c for c in np.flatnonzero(reality.tier[si] == k) if c not in order]
        order += extra
        po = g[g.outcome == "promoted via play-offs"].club_id
        st[k] = (order, reality.ci[po.iloc[0]] if len(po) else None)
    return st


def _season_events(reality, world, season):
    """Departures (leave before balancing), late leavers, scenario removals filled by
    cascade, and entrants for the move from ``season`` to ``season + 1``."""
    dep = list(reality.departures.get(season, []))
    late = dict(reality.late.get(season, {}))
    dep = [c for c in dep if c not in late]
    ghosts = []
    for cid, first in world.removed.items():
        if first == season + 1:
            (ghosts if world.removal_fill == "cascade" else dep).append(reality.ci[cid])
    ent = [c for c in reality.entrants.get(season + 1, [])
           if reality.clubs[c] not in world.removed or world.removed[reality.clubs[c]] > season + 1]
    return dep, late, ent, ghosts


def start_membership(reality, world):
    """Who is in each division in the first simulated season: reality's own
    membership for 2008/09; otherwise the previous real season's final standings
    moved on under the world's rules (so a scenario's first changed season starts
    from real history)."""
    if world.start == FIRST_SEASON:
        si = 0
        return {k: list(np.flatnonzero(reality.tier[si] == k)) for k in TIERS}
    prev = world.start - 1
    dep, late, ent, ghosts = _season_events(reality, world, prev)
    removed_now = [reality.ci[c] for c, f in world.removed.items() if f <= prev]
    st = _real_standings(reality, world, prev)
    st = {k: ([c for c in o if c not in removed_now], p) for k, (o, p) in st.items()}
    new, _ = _transition(reality, world, prev, st, dep, late, ent, ghosts)
    return new


def simulate(world: World, runs: int = 10_000, seed: int = SEED, anchored: bool = True,
             reality: Reality | None = None, verbose: bool = False) -> Simulation:
    """Monte Carlo of ``world`` from ``world.start`` to ``world.end``."""
    R = reality or Reality()
    rng = np.random.default_rng(seed)
    C = len(R.clubs)
    seasons = list(range(world.start, world.end + 1))
    S = len(seasons)
    tier = np.zeros((runs, S + 1, C), np.int8)
    pos = np.zeros((runs, S, C), np.int16)
    pts = np.zeros((runs, S, C), np.int16)
    gp = np.zeros((runs, S, C), np.int16)
    gd = np.zeros((runs, S, C), np.int16)
    out = np.zeros((runs, S, C), np.int8)
    mem0 = start_membership(R, world)
    for k, cl in mem0.items():
        tier[:, 0, cl] = k
    prev_out = np.zeros((runs, C), np.int8)
    for j, s in enumerate(seasons):
        si = s - FIRST_SEASON
        # ratings for the season, one draw per run and club
        z = rng.standard_normal((2, runs, C))
        A = R.att[si] + R.asd[si] * z[0]
        D = R.dfn[si] + R.dsd[si] * z[1]
        cur = tier[:, j, :].astype(int)
        if world.step_up:
            real = np.where(R.tier[si] > 0, R.tier[si], BOTTOM + 1)
            gap = np.where(cur > 0, np.maximum(real[None, :] - cur, 0), 0)
            A -= world.step_up * gap / 2
            D -= world.step_up * gap / 2
        if world.money_boost and j > 0:
            boost = np.isin(prev_out, (AUTO, PLAYOFF)) & (cur > 0) & (cur < np.where(
                R.tier[si] > 0, R.tier[si], BOTTOM + 1)[None, :])
            A += world.money_boost * boost / 2
            D += world.money_boost * boost / 2
        res = {}
        for k in TIERS:
            nk = (cur == k).sum(1)
            orders = [None] * runs
            po_all = np.full(runs, -1)
            # a late leaver's vacancy follows the club, so a division can be one
            # short in some runs: play each division size separately
            for n in np.unique(nk):
                idx = np.flatnonzero(nk == n)
                members = np.sort(np.argsort(cur[idx] != k, axis=1, kind="stable")[:, :n], axis=1)
                dr = _Draws(A[idx], D[idx], R.mu, R.rho)
                order, p_, g_, d_, po = _division(R, world, s, k, members, dr, rng, anchored)
                rows = idx[:, None]
                pos[rows, j, order] = np.arange(1, n + 1)[None, :]
                pts[rows, j, order] = p_
                gp[rows, j, order] = g_
                gd[rows, j, order] = d_
                for i, r in enumerate(idx):
                    orders[r] = order[i].tolist()
                if po is not None:
                    po_all[idx] = po
            res[k] = (orders, po_all)
        # moves into next season, run by run
        dep, late, ent, ghosts = _season_events(R, world, s)
        has_next = (s + 1, 1) in world.sizes
        for r in range(runs):
            st = {k: (res[k][0][r], None if res[k][1][r] < 0 else int(res[k][1][r]))
                  for k in TIERS}
            if has_next:
                new, oc = _transition(R, world, s, st, dep, late, ent, ghosts)
                for k, cl in new.items():
                    tier[r, j + 1, cl] = k
            else:
                oc = _final_outcomes(world, s, st)
            for c, v in oc.items():
                out[r, j, c] = v
            out[r, j, st[1][0][0]] = CHAMPION
        prev_out = out[:, j, :]
        if verbose:
            print(f"  {s} done", flush=True)
    return Simulation(world=world, clubs=R.clubs, seasons=seasons, tier=tier, pos=pos, pts=pts,
                      played=gp, gd=gd, outcome=out, anchored=anchored, seed=seed)


def _final_outcomes(world, season, standings):
    """Outcomes of the last simulated season, when next season's sizes are unknown:
    the season's nominal promotion and relegation places."""
    oc = {}
    for k, (order, po) in standings.items():
        rule = world.rules.loc[(season, k)]
        if k > 1:
            for c in order[:int(rule.auto_up)]:
                oc[c] = AUTO
            if po is not None:
                oc[po] = PLAYOFF
        for c in order[len(order) - int(rule.relegated):]:
            oc[c] = RELEGATED
    return oc
