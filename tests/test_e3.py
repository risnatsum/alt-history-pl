"""Stage E3: the season simulator."""
import numpy as np
import pandas as pd
import pytest

from altpl import outputs as O
from altpl import simulator as S


@pytest.fixture(scope="module")
def R():
    return S.Reality()


def _membership(R, sim, j):
    return {k: set(np.flatnonzero(sim.tier[0, j] == k)) for k in S.TIERS}


def test_reality_reproduced_exactly(R):
    """Every real result kept: every run gives back every real table and move."""
    sim = S.simulate(S.real_world(R), runs=5, reality=R)
    real = R.tier[:sim.tier.shape[1]]
    assert (sim.tier == real[None]).all()
    t = R.tables
    j = t.season.values - S.FIRST_SEASON
    c = t.club_id.map(R.ci).values
    assert (sim.pts[:, j, c] == t.pts.values[None]).all()
    assert ((sim.pos[:, j, c] == t.pos.values[None]) | t.tied.values[None]).all()


def test_moves_from_real_tables_give_real_divisions(R):
    for s in range(2009, 2027):
        m = S.start_membership(R, S.real_world(R, s, min(s, 2025)))
        for k in S.TIERS:
            assert set(m[k]) == set(np.flatnonzero(R.tier[s - S.FIRST_SEASON] == k)), (s, k)


def test_fully_simulated_keeps_division_sizes(R):
    w = S.real_world(R, 2008, 2012)
    sim = S.simulate(w, runs=30, anchored=False, reality=R)
    for j, s in enumerate(sim.seasons):
        for k in S.TIERS:
            assert ((sim.tier[:, j] == k).sum(1) == R.sizes[(s, k)]).all()
        # everyone played a full double round robin, except in runs where a club
        # whose record was expunged that season (it follows the club) is in the division
        exp = [c for ss, c in R.expunged if ss == s]
        for k in S.TIERS:
            n = R.sizes[(s, k)]
            clean = ~(sim.tier[:, j, exp] == k).any(1) if exp else np.ones(sim.runs, bool)
            inn = (sim.tier[:, j] == k) & clean[:, None]
            assert (sim.played[:, j][inn] == 2 * (n - 1)).all()


def test_removed_club_cascade(R):
    """A club removed after 2008/09 is replaced by the best non-promoted club below,
    and so on down the pyramid (the vacancy reduces National League relegation)."""
    w = S.real_world(R, 2009, 2010)
    w.removed = {"manchester_city": 2009}
    m = S.start_membership(R, w)
    real = {k: set(np.flatnonzero(R.tier[1] == k)) for k in S.TIERS}
    city = R.ci["manchester_city"]
    assert city not in set().union(*map(set, m.values()))
    assert set(m[1]) - real[1] == {R.ci["sheffield_united"]}
    for k in S.TIERS:
        assert len(m[k]) == R.sizes[(2009, k)]
    sim = S.simulate(w, runs=10, reality=R)
    assert not (sim.tier[:, :, city] > 0).any()


def test_odd_sized_division(R):
    """A 19-club Premier League: one club idle each round, 36 matches each."""
    w = S.real_world(R, 2009, 2010)
    w.removed = {"manchester_city": 2009}
    for s in (2009, 2010, 2011):
        w.sizes[(s, 1)] = 19
        w.sizes[(s, 2)] = R.sizes[(s, 2)] + 1
    sim = S.simulate(w, runs=10, anchored=False, reality=R)
    for j in range(2):
        inn = sim.tier[:, j] == 1
        assert (inn.sum(1) == 19).all()
        assert (sim.played[:, j][inn] == 36).all()
        assert ((sim.tier[:, j] == 2).sum(1) == 25).all()


def test_real_results_kept_in_a_scenario(R):
    """With City removed, every other real 2009/10 PL fixture keeps its real score:
    a club's points differ from its real points without City games only by its games
    against Sheffield United."""
    w = S.real_world(R, 2009, 2009)
    w.removed = {"manchester_city": 2009}
    sim = S.simulate(w, runs=50, reality=R)
    res = R.results[(R.results.season == 2009) & (R.results.tier == 1)]
    res = res[(res.home_id != "manchester_city") & (res.away_id != "manchester_city")]
    h = pd.DataFrame({"c": res.home_id, "p": np.select([res.hg > res.ag, res.hg == res.ag], [3, 1], 0)})
    a = pd.DataFrame({"c": res.away_id, "p": np.select([res.ag > res.hg, res.hg == res.ag], [3, 1], 0)})
    base = pd.concat([h, a]).groupby("c").p.sum()
    ded = {"portsmouth": 9}
    for c, p in base.items():
        sp = sim.pts[:, 0, R.ci[c]] + ded.get(c, 0)
        assert (sp >= p).all() and (sp <= p + 6).all(), c


def test_outputs_tables(R):
    w = S.real_world(R, 2015, 2015)
    sim = S.simulate(w, runs=50, anchored=False, reality=R)
    e = O.expected_tables(sim, R)
    pl = e[(e.tier == 1)]
    assert len(pl) == 20 and abs(pl.p_title.sum() - 1) < 1e-9
    ch = e[e.tier == 2]
    assert abs(ch.p_promoted.sum() - 3) < 1e-9
    assert abs(ch.p_relegated.sum() - 3) < 1e-9
    c = O.champions(sim, R)
    assert c.loc[c.tier == 1, "real_champion"].item() == "Leicester City"
    ww = O.whos_where(sim)
    p = ww[["p_tier1", "p_tier2", "p_tier3", "p_tier4", "p_tier5", "p_out"]].sum(axis=1)
    assert np.allclose(p, 1)
