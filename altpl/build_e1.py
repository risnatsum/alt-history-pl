"""Stage E1: canonical results, real final tables, and who was where.

    python -m altpl.build_e1

Writes to data/processed/:
  results.csv          one row per league match 2008/09-2025/26
  source_conflicts.csv every fixture where the sources disagreed, and the call made
  tables.csv           real final tables (deductions applied, 2019/20 PPG where used)
  membership.csv       division of every club in every season, 2008/09-2026/27
  real_tables.xlsx     the tables, one sheet per division
and docs/e1_validation.md with the consistency checks.
"""
from __future__ import annotations

import pandas as pd

from altpl.clubs import club_id, club_name
from altpl.config import LAST_SEASON, PROCESSED, REFERENCE, ROOT, SOURCES, TIERS, season_label
from altpl.results import build as build_results
from altpl.tables import all_tables, load_adjustments

FD_DIVS = {"E0": 1, "E1": 2, "E2": 3, "E3": 4, "EC": 5}


def membership(results: pd.DataFrame, adj: pd.DataFrame) -> pd.DataFrame:
    m = pd.concat([results[["season", "tier", "home_id"]].rename(columns={"home_id": "club_id"}),
                   results[["season", "tier", "away_id"]].rename(columns={"away_id": "club_id"})])
    # Clubs whose record was expunged still occupied a place that season.
    ex = adj[adj.type == "expunged"][["season", "tier", "club_id"]]
    # The season after the last finished one, from football-data's current files.
    nxt = []
    for div, tier in FD_DIVS.items():
        f = SOURCES / "footballdata_csv_2627" / f"{LAST_SEASON % 100 + 1:02d}{LAST_SEASON % 100 + 2:02d}_{div}.csv"
        d = pd.read_csv(f, encoding="latin-1").dropna(subset=["HomeTeam"])
        nxt += [(LAST_SEASON + 1, tier, club_id(n, LAST_SEASON + 1))
                for n in set(d.HomeTeam) | set(d.AwayTeam)]
    m = pd.concat([m, ex, pd.DataFrame(nxt, columns=["season", "tier", "club_id"])])
    return m.drop_duplicates().sort_values(["season", "tier", "club_id"]).reset_index(drop=True)


def label_outcomes(tables: pd.DataFrame, mem: pd.DataFrame) -> pd.DataFrame:
    rules = pd.read_csv(REFERENCE / "seasons.csv", comment="#")
    exc = pd.read_csv(REFERENCE / "movement_exceptions.csv", comment="#")
    nxt = {(s - 1, c): t for s, t, c in mem.itertuples(index=False)}
    t = tables.merge(rules[["season", "tier", "auto_up", "playoff_from", "playoff_to",
                            "relegated"]], on=["season", "tier"], how="left")
    t["next_tier"] = [nxt.get((s, c)) for s, c in zip(t.season, t.club_id)]
    n = t.groupby(["season", "tier"]).pos.transform("max")
    exc_map = {(r.season, r.tier, r.club_id): r.event for r in exc.itertuples()}

    def outcome(r) -> str:
        ev = exc_map.get((r.season, r.tier, r.club_id))
        if ev in ("expelled", "demoted"):
            return ev
        if ev == "relegated_wound_up":
            return "relegated"
        up = pd.notna(r.next_tier) and r.next_tier < r.tier
        if r.tier == 1 and r.pos == 1:
            return "champions"
        if up:
            return "promoted" if r.pos <= r.auto_up else "promoted via play-offs"
        if pd.notna(r.next_tier) and r.next_tier > r.tier or (pd.isna(r.next_tier) and r.tier == 5):
            return "relegated" if ev is None else ev
        return ev or ""

    t["outcome"] = t.apply(outcome, axis=1)
    t["expected"] = ""
    t.loc[t.pos <= t.auto_up, "expected"] = "auto up"
    t.loc[(t.pos >= t.playoff_from) & (t.pos <= t.playoff_to) & (t.playoff_to > 0), "expected"] = "play-offs"
    t.loc[t.pos > n - t.relegated, "expected"] = "down"
    return t.drop(columns=["auto_up", "playoff_from", "playoff_to", "relegated"])


def check(t: pd.DataFrame) -> list[str]:
    """Every real move must match the league position under that season's rules,
    unless it is a documented exception."""
    problems = []
    for r in t.itertuples():
        if r.season == LAST_SEASON + 1:
            continue
        o, e = r.outcome, r.expected
        bad = ((o == "promoted" and e != "auto up") or
               (o == "promoted via play-offs" and e != "play-offs") or
               (o == "relegated" and e != "down") or
               (e == "auto up" and not o.startswith("promoted") and o != "expelled") or
               (e == "down" and o not in ("relegated", "expelled", "demoted", "reprieved")))
        if bad:
            problems.append(f"{season_label(r.season)} {TIERS[r.tier]}: {club_name(r.club_id)} "
                            f"finished {r.pos} ({r.pts} pts) but outcome was '{o or 'stayed'}'")
    for (s, tier), g in t.groupby(["season", "tier"]):
        n_po = (g.outcome == "promoted via play-offs").sum()
        if tier > 1 and n_po != 1:
            problems.append(f"{season_label(s)} {TIERS[tier]}: {n_po} play-off winners found")
    return problems


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    results, conflicts = build_results()
    results.to_csv(PROCESSED / "results.csv", index=False)
    conflicts.to_csv(PROCESSED / "source_conflicts.csv", index=False)

    adj = load_adjustments()
    tables = all_tables(results, adj)
    mem = membership(results, adj)
    mem.to_csv(PROCESSED / "membership.csv", index=False)
    t = label_outcomes(tables, mem)
    t.insert(4, "club", t.club_id.map(club_name))
    t.to_csv(PROCESSED / "tables.csv", index=False)

    cols = ["season", "pos", "club", "p", "w", "d", "l", "gf", "ga", "gd", "pts_raw",
            "deduction", "pts", "ppg", "outcome"]
    with pd.ExcelWriter(PROCESSED / "real_tables.xlsx") as xw:
        for tier, name in TIERS.items():
            x = t[t.tier == tier][cols].copy()
            x["season"] = x.season.map(season_label)
            x.to_excel(xw, sheet_name=name, index=False)
        adj.to_excel(xw, sheet_name="Adjustments", index=False)

    problems = check(t)
    ties = t[t.tied][["season", "tier", "pos", "club", "pts", "gd", "gf"]]
    write_report(results, conflicts, t, problems, ties)
    print(f"{len(results)} results, {len(t)} table rows, {len(problems)} problems")
    for p in problems:
        print("  ", p)


def write_report(results, conflicts, t, problems, ties) -> None:
    by = results.groupby(["season", "tier"]).size().unstack()
    nsrc = results.groupby(["season", "tier"]).n_sources.min().unstack()
    lines = ["# E1 validation report", "",
             "Generated by `python -m altpl.build_e1`. Do not edit by hand.", "",
             "## Matches per division and season", "",
             "| Season | " + " | ".join(TIERS.values()) + " |",
             "|---|" + "---|" * len(TIERS)]
    for s, row in by.iterrows():
        cells = [f"{int(row[k])} ({int(nsrc.loc[s, k])})" for k in TIERS]
        lines.append(f"| {season_label(s)} | " + " | ".join(cells) + " |")
    lines += ["", "Bracket: the smallest number of independent sources behind any match "
              "in that division and season.", "",
              "## Source disagreements", "",
              f"{len(conflicts)} fixtures had sources disagreeing on the score.", ""]
    if len(conflicts):
        summ = conflicts.groupby(["season", "tier", "basis"]).size().reset_index(name="n")
        lines += ["| Season | Division | How settled | Fixtures |", "|---|---|---|---|"]
        lines += [f"| {season_label(r.season)} | {TIERS[r.tier]} | {r.basis} | {r.n} |"
                  for r in summ.itertuples()]
    lines += ["", "## Final positions against real promotions and relegations", "",
              "Each club's division the following season is compared with where it finished "
              "under that season's rules (data/reference/seasons.csv), allowing for the "
              "documented exceptions in data/reference/movement_exceptions.csv.", ""]
    lines += ([f"- {p}" for p in problems] if problems else ["All consistent."])
    lines += ["", "## Ties not broken by points, goal difference and goals scored", ""]
    lines += ([f"- {season_label(r.season)} {TIERS[r.tier]}: {r.club} (pos {r.pos}, {r.pts} pts, "
               f"GD {r.gd}, GF {r.gf})" for r in ties.itertuples()] if len(ties) else ["None."])
    lines += ["", "## Champions", "", "| Season | " + " | ".join(TIERS.values()) + " |",
              "|---|" + "---|" * len(TIERS)]
    champ = t[(t.pos == 1)].pivot(index="season", columns="tier", values="club")
    for s, row in champ.iterrows():
        lines.append(f"| {season_label(s)} | " + " | ".join(row[k] for k in TIERS) + " |")
    (ROOT / "docs" / "e1_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
