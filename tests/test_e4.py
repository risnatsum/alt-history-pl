"""Stage E4: the finance model."""
import numpy as np
import pandas as pd
import pytest

from altpl import build_e4 as B
from altpl import finance as F
from altpl import finance_data as FD
from altpl import simulator as S
from altpl.config import PROCESSED


@pytest.fixture(scope="module")
def R():
    return S.Reality()


@pytest.fixture(scope="module")
def P():
    FD.main()
    return F.Prices()


def test_price_list_complete(P):
    """Every item has a value for every season it applies to, and every value says
    where it came from."""
    p = pd.read_csv(PROCESSED / "finance_prices.csv")
    assert set(p.status) <= {"sourced", "derived", "estimate", "filled"}
    assert p[p.status == "filled"].basis.notna().all()
    for item in ["pl_base", "pl_merit_unit", "pl_fac_slope", "parachute_y1", "parachute_y2",
                 "solidarity_t2", "solidarity_t3", "solidarity_t4", "efl_t2", "efl_t3", "efl_t4",
                 "uefa_UCL", "uefa_UEL", "cpi"]:
        assert set(p[p["item"] == item].season) == set(FD.SEASONS), item
    # anything not filled carries a source URL
    assert (p[p.status.isin(["sourced", "estimate"])].source.str.startswith("http")).all()


def test_reality_gives_zero_difference(R, P):
    sim = S.simulate(S.real_world(R), runs=3, reality=R)
    fr = F.finance(sim, R, P)
    assert len(fr.club_total) == 0 or np.allclose(fr.club_total.total_mean, 0)
    assert np.allclose(fr.club_season.diff_mean, 0)


def test_parachute_recipients_match_sources(R, P):
    m = B.real_revenue(R, P)
    assert B.parachute_check(m).match.all()


def test_one_season_rule(R, P):
    """Norwich went down in 2016 after one PL season: years 1-2 only (2016/17, 2017/18)."""
    m = B.real_revenue(R, P).set_index(["club_id", "season"])
    assert m.loc[("norwich_city", 2016)].parachute > 0
    assert m.loc[("norwich_city", 2017)].parachute > 0
    assert m.loc[("norwich_city", 2018)].parachute == 0
    # Aston Villa (many PL seasons) get a third year in 2018/19
    assert m.loc[("aston_villa", 2018)].parachute > 0


def test_promotion_in_a_run_is_priced(R, P):
    """Move one club up a division in a copy of reality: its PL money appears, its
    Championship money goes, and next season it gets a parachute."""
    sim = S.simulate(S.real_world(R, 2015, 2016), runs=2, reality=R)
    c = R.ci["brentford"]  # Championship in 2015/16 and 2016/17
    w = R.ci["aston_villa"]  # PL 2015/16, relegated
    sim.tier[:, 0, [c, w]] = sim.tier[:, 0, [w, c]]
    sim.pos[:, 0, [c, w]] = sim.pos[:, 0, [w, c]]
    fr = F.finance(sim, R, P)
    d = fr.club_season.set_index(["club_id", "season"])
    assert d.loc[("brentford", 2015)].diff_pl_central > 50e6
    assert d.loc[("brentford", 2015)].diff_efl_central < 0
    assert d.loc[("brentford", 2016)].diff_parachute > 0      # went down from the PL in the run
    assert d.loc[("aston_villa", 2015)].diff_pl_central < -50e6


def test_pl_payment_falls_with_position(P):
    pos = np.arange(1, 21)
    for s in FD.SEASONS:
        pay = P.pl_central(s, pos)
        assert (np.diff(pay) < 0).all(), s
