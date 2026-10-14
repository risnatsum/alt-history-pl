"""Write docs/e2_validation.md and data/processed/e2_backtest.xlsx from the E2 outputs."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from altpl.backtest import calibration_bins, match_metrics
from altpl.config import PROCESSED, ROOT, TIERS, season_label
from altpl.build_e2 import TOL

KINDS = {"insample": "In-sample (full-season ratings)",
         "midseason": "Mid-season (first half known)",
         "preseason": "Pre-season (earlier seasons only)"}
EVENTS = [("p_title", "title", "Division winner"), ("p_auto", "auto", "Automatic promotion"),
          ("p_playoff", "playoff", "Play-off place"), ("p_promoted", "promoted", "Promoted"),
          ("p_releg", "releg_zone", "Relegation zone")]


def md(df: pd.DataFrame, floatfmt="{:.3f}") -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for row in df.itertuples(index=False):
        cells = [floatfmt.format(v) if isinstance(v, (float, np.floating)) and not pd.isna(v)
                 else ("" if pd.isna(v) else str(v)) for v in row]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def match_tables(ho: pd.DataFrame):
    rows = []
    res = np.select([ho.hg > ho.ag, ho.hg == ho.ag], [0, 1], 2)
    base = pd.DataFrame(np.eye(3)[res]).groupby(ho.tier.values).transform("mean").values
    for tier, g in [("All", ho)] + [(TIERS[t], ho[ho.tier == t]) for t in range(1, 6)]:
        idx = g.index
        mk = g[["market_pH", "market_pD", "market_pA"]].notna().all(1)
        for name, cols in [("Model, held out", ["model_pH", "model_pD", "model_pA"]),
                           ("Bookmakers (benchmark)", ["market_pH", "market_pD", "market_pA"])]:
            x = match_metrics(g.loc[mk, cols].values, g[mk])
            rows.append({"division": tier, "predictor": name, **x})
        x = match_metrics(base[ho.index.get_indexer(idx[mk])], g[mk])
        rows.append({"division": tier, "predictor": "Home/draw/away base rates", **x})
    return pd.DataFrame(rows)


def event_clubs(g: pd.DataFrame, hcol: str) -> pd.DataFrame:
    """Clubs in division-seasons where the event exists (no promotion from the PL,
    no relegation zone in 2020/21 National League)."""
    if hcol == "title":
        return g
    if hcol == "releg_zone":
        return g[g.groupby(["season", "tier"]).releg_zone.transform("any")]
    return g[g.tier > 1]


def season_summaries(s: pd.DataFrame):
    s = s.assign(err=s.xpts - s.pts)
    s["naive_err"] = s.groupby(["kind", "season", "tier"]).pts.transform("mean") - s.pts
    pts = s.groupby(["kind", "tier"]).apply(lambda g: pd.Series({
        "division-seasons": g[["season"]].drop_duplicates().shape[0],
        "points RMSE": np.sqrt((g.err ** 2).mean()),
        "naive RMSE": np.sqrt((g.naive_err ** 2).mean()),
        "share of real points inside 5-95% range": ((g.pts >= g.pts_p05) & (g.pts <= g.pts_p95)).mean()}),
        include_groups=False).reset_index()
    pts["division"] = pts.tier.map(TIERS)
    pts["kind"] = pts.kind.map(KINDS)
    ev = []
    for k, g in s.groupby("kind"):
        for pcol, hcol, name in EVENTS:
            gg = event_clubs(g, hcol)
            hit = gg[hcol].astype(float)
            b = ((gg[pcol] - hit) ** 2).mean()
            b0 = ((gg.groupby(["season", "tier"])[hcol].transform("mean") - hit) ** 2).mean()
            ev.append({"kind": KINDS[k], "event": name, "clubs": len(gg), "Brier": b,
                       "Brier if no skill": b0, "skill": 1 - b / b0})
    return pts, pd.DataFrame(ev), s


def write_report():
    params = json.loads((PROCESSED / "ratings_params.json").read_text())
    tuning = pd.read_csv(PROCESSED / "e2_tuning.csv")
    ho = pd.read_csv(PROCESSED / "e2_holdout_matches.csv")
    seasons = pd.read_csv(PROCESSED / "e2_backtest_seasons.csv")
    lv = pd.read_csv(PROCESSED / "division_levels.csv")
    ratings = pd.read_csv(PROCESSED / "ratings.csv")

    mt = match_tables(ho)
    pts, ev, s = season_summaries(seasons)
    res = np.select([ho.hg > ho.ag, ho.hg == ho.ag], [0, 1], 2)
    p_res = ho[["model_pH", "model_pD", "model_pA"]].values
    match_cal = calibration_bins(p_res.ravel(), np.eye(3)[res].ravel())

    ev_cal = []
    for k, g in s.groupby("kind"):
        for pcol, hcol, name in EVENTS:
            gg = event_clubs(g, hcol)
            c = calibration_bins(gg[pcol].values, gg[hcol].astype(float).values)
            ev_cal.append(c.assign(kind=KINDS[k], event=name))
    ev_cal = pd.concat(ev_cal)

    # movers: pre-season forecasts for clubs that changed division
    pre = s[s.kind == "preseason"].copy()
    prev = ratings[["season", "club_id", "tier"]].assign(season=lambda d: d.season + 1) \
        .rename(columns={"tier": "prev_tier"})
    pre = pre.merge(prev, on=["season", "club_id"], how="left")
    pre["group"] = np.select([pre.prev_tier.isna(), pre.prev_tier > pre.tier,
                              pre.prev_tier < pre.tier], ["new to the data", "promoted into division",
                                                          "relegated into division"], "same division")
    mov = pre.groupby(["tier", "group"]).agg(clubs=("club_id", "size"),
                                             mean_expected_pts=("xpts", "mean"),
                                             mean_actual_pts=("pts", "mean"),
                                             mean_error=("err", lambda e: -e.mean()),
                                             se=("err", lambda e: e.std() / np.sqrt(len(e)))).reset_index()
    mov["division"] = mov.tier.map(TIERS)

    champs = s[(s.tier == 1) & (s.pos == 1)][["kind", "season", "club_id", "p_title"]]
    champs = champs.pivot(index=["season", "club_id"], columns="kind", values="p_title").reset_index()
    champs["season"] = champs.season.map(season_label)

    lv_w = lv.pivot(index="season", columns="tier", values="gap_to_tier_above")[[2, 3, 4, 5]]
    lv_w.columns = [f"{TIERS[t - 1]} minus {TIERS[t]}" for t in lv_w.columns]
    lv_w = lv_w.reset_index()
    lv_w["season"] = lv_w.season.map(season_label)
    xg = lv[lv.tier > 1].groupby("tier")[["gap_to_tier_above", "xg_for_v_tier_above",
                                          "xg_against_v_tier_above", "movers_from_or_to_tier_above"]].mean().reset_index()
    xg["boundary"] = [f"{TIERS[t - 1]} / {TIERS[t]}" for t in xg.tier]

    with pd.ExcelWriter(PROCESSED / "e2_backtest.xlsx") as xw:
        ratings.to_excel(xw, sheet_name="ratings", index=False)
        lv.to_excel(xw, sheet_name="division_levels", index=False)
        tuning.to_excel(xw, sheet_name="tuning", index=False)
        mt.to_excel(xw, sheet_name="match_accuracy", index=False)
        match_cal.astype({"bin": str}).to_excel(xw, sheet_name="match_calibration", index=False)
        pts.to_excel(xw, sheet_name="points_error", index=False)
        ev.to_excel(xw, sheet_name="event_summary", index=False)
        ev_cal.astype({"bin": str}).to_excel(xw, sheet_name="event_calibration", index=False)
        mov.to_excel(xw, sheet_name="movers_preseason", index=False)
        champs.to_excel(xw, sheet_name="champions", index=False)
        s.to_excel(xw, sheet_name="all_clubs", index=False)

    hs = params["home_season"]
    L = []
    w = L.append
    w("# Stage E2 validation: ratings model and back-test\n")
    w("Generated by `python -m altpl.build_e2`. Every number below is a model estimate "
      "from real results and bookmaker odds, not a fact. The spreadsheet "
      "`data/processed/e2_backtest.xlsx` has every table in full.\n")
    w("## Model\n")
    w("Dixon-Coles Poisson model, one attack and one defence rating per club per season, "
      "home advantage per season plus a per-division adjustment, fitted to all "
      f"{len(ho):,} league matches 2008/09–2025/26 in tiers 1–5 at once. Divisions are put on "
      "one scale by tying each club's ratings to its previous season's (a random walk), so "
      "clubs that move between divisions fix the gap between them. Bookmaker odds enter as "
      "the expected goals they imply, counted as extra fractional goals. See "
      "`altpl/ratings.py` and the E2 entries in `docs/assumptions_log.md`.\n")
    w(f"- Season-to-season change in a club's ratings (sigma): **{params['sigma']}** "
      "per season, chosen by pre-season log-loss.")
    w(f"- Weight on the odds (omega): **{params['omega']}** (1 = the market's view of a match "
      "counts as much as its score), chosen by held-out log-loss.")
    w(f"- Dixon-Coles rho: {params['rho']:.3f}. Average home advantage: "
      f"{np.mean(list(hs.values())):.3f} on the log scale; 2020/21 (no crowds): {hs['2020']:.3f}.")
    w("- Ratings are scaled so the average Premier League club-season has attack 0. "
      "Strength = attack + defence; a 0.1 gap is roughly 10% more goals scored and 10% fewer conceded.\n")
    w("### Tuning\n")
    pre = tuning[tuning.step == "pre-season"][["sigma", "omega", "matches", "log_loss", "accuracy"]]
    w("sigma, chosen by how well each season's matches are predicted from earlier seasons "
      "only (2010/11–2025/26; 1X2 log-loss, lower is better):\n")
    w(md(pre, "{:.4f}") + "\n")
    hot = tuning[tuning.step == "held-out"][["sigma", "omega", "log_loss", "brier",
                                              "accuracy", "score_log_loss"]]
    w("omega, chosen by 5-fold held-out matches within each season (section 1): the "
      f"smallest weight within {TOL} log-loss of the best.\n")
    w(md(hot, "{:.4f}") + "\n")

    w("## 1. Held-out matches\n")
    w("Each season's matches were split into five groups at random; each group was predicted "
      "by ratings fitted without it (its scores and its odds hidden). This is the job the "
      "ratings do in a scenario: rate a club from its real season and predict a fixture "
      "that never happened. The bookmakers' own closing-average odds for the same matches "
      "are shown as the benchmark the model is trying to approach; they are not available "
      "for fixtures that never happened.\n")
    w(md(mt[["division", "predictor", "matches", "log_loss", "brier", "accuracy"]]) + "\n")
    w("Calibration of the held-out home/draw/away probabilities (all outcomes pooled):\n")
    w(md(match_cal.astype({"bin": str})) + "\n")

    w("## 2. The gap between divisions\n")
    w("Average strength gap between neighbouring divisions, per season (strength = attack + "
      "defence, same scale everywhere):\n")
    w(md(lv_w) + "\n")
    w("Average over all seasons, with what it means for an average club of the lower "
      "division playing an average club of the higher one at a neutral ground (expected "
      "goals for and against), and how many clubs per season move across that boundary:\n")
    w(md(xg[["boundary", "gap_to_tier_above", "xg_for_v_tier_above",
             "xg_against_v_tier_above", "movers_from_or_to_tier_above"]]) + "\n")
    w("**Check on the gap: clubs that changed division.** Pre-season forecasts (ratings from "
      "earlier seasons only, no adjustment beyond the common scale) of clubs promoted or "
      "relegated into a division, against what they scored. A positive error means the "
      "clubs did better than predicted.\n")
    w(md(mov[["division", "group", "clubs", "mean_expected_pts", "mean_actual_pts",
              "mean_error", "se"]], "{:.1f}") + "\n")

    w("## 3. Simulated vs real tables\n")
    w("Each season re-simulated 10,000 times per information set, with real points "
      "deductions applied. 2019/20 League One, League Two and National League are left out "
      "(curtailed and decided on points per game). Pre-season starts at 2010/11 because "
      "the scale between divisions needs at least one season of movers. Naive RMSE gives "
      "every club the division's average points.\n")
    p2 = pts[["kind", "division", "division-seasons", "points RMSE", "naive RMSE",
              "share of real points inside 5-95% range"]]
    w(md(p2, "{:.2f}") + "\n")

    w("## 4. Do title, promotion and relegation odds come true?\n")
    w("Brier score of each club's probability (lower is better). 'Brier if no skill' gives "
      "every club in a division the same probability; skill = 1 − Brier / no-skill Brier.\n")
    w(md(ev, "{:.3f}") + "\n")
    w("Calibration by probability band (pre-season and mid-season):\n")
    for k in ("preseason", "midseason"):
        for _, _, name in EVENTS:
            if name not in ("Promoted", "Relegation zone", "Division winner"):
                continue
            c = ev_cal[(ev_cal.kind == KINDS[k]) & (ev_cal.event == name)]
            w(f"**{KINDS[k]}: {name.lower()}**\n")
            w(md(c[["bin", "n", "predicted", "observed"]].astype({"bin": str})) + "\n")

    w("## 5. Champions\n")
    w("The real Premier League champion's simulated title chance under each information set:\n")
    cc = champs.rename(columns=KINDS)
    w(md(cc, "{:.2f}") + "\n")
    (ROOT / "docs" / "e2_validation.md").write_text("\n".join(L), encoding="utf-8")
