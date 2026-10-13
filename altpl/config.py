"""Project-wide constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"            # downloaded source files (not committed)
SOURCES = ROOT / "data" / "sources"    # standardised extracts of each source (committed)
REFERENCE = ROOT / "data" / "reference"
PROCESSED = ROOT / "data" / "processed"

FIRST_SEASON = 2008   # 2008/09
LAST_SEASON = 2025    # 2025/26, the latest finished season as of Oct 2026
SEASONS = range(FIRST_SEASON, LAST_SEASON + 1)

TIERS = {1: "Premier League", 2: "Championship", 3: "League One", 4: "League Two",
         5: "National League"}

# Pinned source snapshots, so every build reads identical inputs.
OPENFOOTBALL = ("openfootball/england", "b17e8f01707d83d2ce1790c14d4a5eeb35987825")
ENGSOCCERDATA = ("jalapic/engsoccerdata", "872c5c354161ace8408f3091b758c6af4cccca94")
# GitHub mirror of football-data.co.uk results and odds (football-data.co.uk itself
# is not reachable from the build environment).
FOOTBALLDATA_MIRROR = ("xgabora/Club-Football-Match-Data-2000-2025",
                       "25882a58a736daf7ece3781940eac17ae1117a66")


def season_label(s: int) -> str:
    return f"{s}/{str(s + 1)[2:]}"
