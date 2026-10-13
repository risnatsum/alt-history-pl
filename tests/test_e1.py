"""Stage E1 checks: parser, table rules, and real outcomes the tables must reproduce."""
from pathlib import Path

import pandas as pd
import pytest

from altpl.build_e1 import check, label_outcomes
from altpl.config import PROCESSED
from altpl.sources.openfootball import parse_file
from altpl.tables import table


def test_parser_handles_both_layouts(tmp_path: Path):
    f = tmp_path / "x.txt"
    f.write_text(
        "▪ Matchday 1\nSat Aug 16\n"
        "  12:45  Arsenal FC               1-0 (1-0)  West Bromwich Albion\n"
        "         Hull City                2-1  Fulham FC\n"
        "  Sat Jan 3 2009\n"
        "    15:00  Boston United   v Morecambe FC   0-4 (0-2)\n"
        "           Bristol Rovers  -  Ipswich Town  [cancelled]\n"
        "▪ Playoffs\nSat May 2\n  15:00  Burnley FC  1-0  Sheffield United\n", encoding="utf-8")
    m = parse_file(f, 2008)
    assert [(x.home, x.away, x.hg, x.ag, x.stage) for x in m] == [
        ("Arsenal FC", "West Bromwich Albion", 1, 0, "league"),
        ("Hull City", "Fulham FC", 2, 1, "league"),
        ("Boston United", "Morecambe FC", 0, 4, "league"),
        ("Burnley FC", "Sheffield United", 1, 0, "playoff")]
    assert str(m[0].date) == "2008-08-16" and str(m[2].date) == "2009-01-03"


def test_table_ranks_by_points_gd_gf_and_ppg():
    r = pd.DataFrame({"home_id": ["a", "b", "c", "a"], "away_id": ["b", "c", "a", "c"],
                      "hg": [2, 1, 0, 0], "ag": [0, 1, 3, 0]})
    t = table(r, {"a": 3})
    assert list(t.club_id) == ["a", "c", "b"]
    assert t.set_index("club_id").pts.to_dict() == {"a": 4, "b": 1, "c": 2}
    t = table(r, ppg=True)
    assert t.iloc[0].club_id == "a" and t.iloc[0].ppg == pytest.approx(7 / 3)


@pytest.fixture(scope="module")
def tables():
    return pd.read_csv(PROCESSED / "tables.csv")


# Real final positions and points (after deductions) the tables must reproduce.
KNOWN = [
    (2008, 2, "sheffield_united", 3, 80),   # Scenario 1A: best non-promoted club in 2008/09
    (2008, 2, "reading", 4, 77),
    (2008, 2, "preston_north_end", 6, 74),  # ahead of Cardiff on goals scored
    (2008, 4, "luton_town", 24, 26),        # -30
    (2009, 1, "portsmouth", 20, 19),        # -9
    (2015, 1, "leicester_city", 1, 81),
    (2017, 1, "manchester_city", 1, 100),
    (2018, 2, "birmingham_city", 17, 52),   # -9
    (2019, 1, "liverpool", 1, 99),
    (2019, 2, "wigan_athletic", 23, 47),    # -12, relegated
    (2019, 3, "bolton_wanderers", 23, 14),  # -12, PPG season
    (2019, 4, "macclesfield_town", 24, 19), # -17, PPG season
    (2020, 2, "sheffield_wednesday", 24, 41),
    (2021, 2, "derby_county", 23, 34),      # -21
    (2021, 2, "reading", 21, 41),           # -6
    (2022, 2, "wigan_athletic", 24, 42),    # -3
    (2023, 1, "everton", 15, 40),           # -8
    (2023, 1, "nottingham_forest", 17, 32), # -4
]


@pytest.mark.parametrize("season,tier,club,pos,pts", KNOWN)
def test_known_final_positions(tables, season, tier, club, pos, pts):
    r = tables[(tables.season == season) & (tables.tier == tier) & (tables.club_id == club)]
    assert (int(r.pos.iloc[0]), int(r.pts.iloc[0])) == (pos, pts)


def test_division_sizes(tables):
    n = tables.groupby(["season", "tier"]).size()
    assert n.xs(1, level="tier").eq(20).all()
    assert n[(2019, 3)] == 23 and n[(2009, 5)] == 23 and n[(2020, 5)] == 22


def test_real_moves_match_final_positions(tables):
    assert check(tables) == []
