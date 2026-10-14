"""Stage E2 checks: odds conversion, score sampling and the cross-division scale."""
import numpy as np
import pandas as pd
import pytest
from scipy.stats import poisson

from altpl.backtest import sample_scores
from altpl.ratings import fit, implied_goals, outcome_probs, score_grid


def test_implied_goals_recovers_poisson_rates():
    lam, nu = np.array([1.2, 2.1, 0.8]), np.array([1.0, 0.7, 1.6])
    p = outcome_probs(lam, nu, 0.0)
    over = 1 - poisson.cdf(2, lam + nu)
    h, a = implied_goals(p[:, 0], p[:, 2], over)
    assert h == pytest.approx(lam, abs=1e-4) and a == pytest.approx(nu, abs=1e-4)
    h, a = implied_goals(p[:, 0], p[:, 2], np.full(3, np.nan))  # 1X2 only
    assert h == pytest.approx(lam, abs=0.05) and a == pytest.approx(nu, abs=0.05)


def test_sampler_matches_dixon_coles_grid():
    rng = np.random.default_rng(1)
    lam, nu, rho = np.full(200_000, 1.4), np.full(200_000, 1.1), -0.1
    x, y = sample_scores(lam, nu, rho, rng)
    g = score_grid(1.4, 1.1, rho)[0]
    for i, j in [(0, 0), (1, 0), (0, 1), (1, 1), (2, 1)]:
        assert ((x == i) & (y == j)).mean() == pytest.approx(g[i, j], abs=0.004)


def _synthetic(gap=0.8, seasons=6, n=10, seed=0):
    """Two divisions; the top two of the lower division swap with the bottom two of
    the upper each season, keeping their strength (plus a little drift)."""
    rng = np.random.default_rng(seed)
    clubs = [f"c{i}" for i in range(2 * n)]
    strength = {c: rng.normal(0, 0.25) - (gap if i >= n else 0) for i, c in enumerate(clubs)}
    tier = {c: 1 if i < n else 2 for i, c in enumerate(clubs)}
    rows = []
    for s in range(seasons):
        for c in clubs:
            strength[c] += rng.normal(0, 0.05)
        pts = {c: 0 for c in clubs}
        for h in clubs:
            for a in clubs:
                if h == a or tier[h] != tier[a]:
                    continue
                lam = np.exp(0.2 + 0.25 + (strength[h] - strength[a]) / 2)
                nu = np.exp(0.2 + (strength[a] - strength[h]) / 2)
                hg, ag = rng.poisson(lam), rng.poisson(nu)
                pts[h] += 3 * (hg > ag) + (hg == ag)
                pts[a] += 3 * (ag > hg) + (hg == ag)
                rows.append((s, tier[h], h, a, hg, ag))
        top = sorted([c for c in clubs if tier[c] == 1], key=pts.get)
        low = sorted([c for c in clubs if tier[c] == 2], key=pts.get, reverse=True)
        for c in top[:2]:
            tier[c] = 2
        for c in low[:2]:
            tier[c] = 1
    m = pd.DataFrame(rows, columns=["season", "tier", "home_id", "away_id", "hg", "ag"])
    m["xh"] = m["xa"] = np.nan
    return m


def test_movers_put_divisions_on_one_scale():
    r = fit(_synthetic(), sigma=0.1, omega=0.0)
    t = r.teams
    gap = (t[t.tier == 1].groupby("season").strength.mean()
           - t[t.tier == 2].groupby("season").strength.mean()).mean()
    # true average gap starts at 0.8 and shrinks a little as the best lower clubs move up
    assert 0.5 < gap < 1.1
