# Notes: gaps, conflicts, doubts

Method: WebSearch + WebFetch only (curl to wikipedia/ons blocked by proxy). WebFetch answers come from a summarising model; key numbers were re-fetched narrowly where surprising (EFL 2024/25 figures, ONS CPI, QPR 2013/14). Units: parachute.csv amounts in £m; solidarity/efl_basic in £.

## Parachute
- **2008/09: no amount found.** 2009/10 only from sportingintelligence (£12.4m for Y1 and Y2).
- **2010/11: no PL-published figure found.** Only Swiss Ramble's club-accounts "£15 million" (Burnley) and theesk's 16.0 (scheme-nominal). Pre-2016 actual payments are consistently ~47-50% of the TV equal share, below the nominal £16m/£23m/£25m scheme numbers quoted in blogs.
- **Year 2/3/4 actuals 2010/11-2013/14 are missing** (sportingintelligence tables were images). 2012/13 known only as a range £5.7m-£15.7m; which year each end belongs to is inference.
- theesk (Aug 2025) table shows flat 16/16/8/8 for every relegation 2009/10-2013/14 and ~44 for 2022/23 relegations; it conflicts with sportingintelligence actuals (15.475 in 2011/12; 25 in 2014/15) and with EFL's 47.6 (2022/23). Treated as low confidence.
- Wikipedia's 2019/20-2022/23 per-club figures are flagged "est." on the page; EFL's 2022/23 figures (47.6/38.9/17.3) are higher than Wikipedia's 44.4/36.3. Prefer EFL.
- Wilson et al. 2019/20 projection (46.75/38.25/17) conflicts with Wikipedia est. (41.3/33.8/15.0).
- **2023/24: only theesk approximations (~44/~36/~16).** **2025/26: only theballbusiness (~49 Y1, ~40 Y2; article self-contradicts with "~£56m").** Year 3 2025/26 missing.
- Sky (Jun 2015) projected 2015/16 Y1 £24m vs actual £25,937,356 - possibly net vs gross of £2.3m solidarity.
- QPR year 2 2016/17: Wikipedia 31.1 vs Swiss Ramble thread 31.2.
- Wikipedia lists Norwich 43.1 in 2018/19 - likely an error.
- EFL: "£233m to 5 clubs" in 2020/21 vs Wikipedia est. listing 7 recipients (3x43.4 + 2x35.5 + 2x15.8 = 233.4). The sum matches £233m so "5 clubs" in the EFL text is probably wrong.
- Rule history conflict: Wikipedia says original scheme = half basic TV money x2 seasons; CSB/Evans say 55%/45%. 2009/10 actual (£12.4m both years) supports "half".
- Percentages pre-2016 in parachute.csv are derived by me from the per-club amounts and the published equal shares (marked "derived"); the base for 2015/16 includes commercial, so not comparable.

## Solidarity
- Missing: 2008/09 (only "£1m from 2006/07" per Wikipedia and £1m in 2009/10), 2013/14 (no source; £2.2m to 2012/13 and £2.3m from 2014/15), L1/L2 for 2009/10 (except Leeds' £0.1m), 2013/14, 2016/17, 2017/18, 2020/21, 2021/22, all divisions 2021/22 and 2025/26.
- 2019/20 conflict: PoF 4.5m/670k/450k vs Wilson 5.1m/760k/510k.
- League Two: £520,000 (2022/23) vs £408,315 (2024/25) - a fall despite higher year-3 parachute; £408,315 is ~2.3% not 3% of £17.8m. DotEcon says L2 rate 3.5%. Unresolved; could be a typo in EFL evidence or a changed split.
- Swiss Ramble (2012) says Championship solidarity went up from "£1.3 million" to £2.2m; Swansea post says from £1m.
- National League: only a total (£4.8m + £1m NL Trust, 2024/25, theesk secondary). No per-club figure found.

## EFL basic award
- Sparse; mostly Swiss Ramble/PoF single-club citations. Championship: 2.47m (09/10), 1.0m (10/11, unexplained drop), 2.5m (11/12), 1.9m (13/14), 1.7m (14/15, 15/16), 2.3m (16/17, 17/18). League One/Two only c.2017/18 (345k/230k) and Leeds 09/10 L1 0.64m. 2018/19-2023/24 nothing. 2024/25 only estimate ranges (theesk) which contradict its own £472k L2 figure.
- The EFL switched to a new Sky deal from 2024/25 (£895m/5 yrs guaranteed, uplift split 80/12/8; Derby County Q&A https://www.dcfc.co.uk/news/2023/05/efl-sky-sports-broadcast-rights-agreement-questions-and-answers) - pre-2024 split approx 70/18/12 Champ/L1/L2; no per-club amount given.
- Unused low-quality sources (not in CSVs): footballtransfers May 2026 (euro figures), thinkfootballideas, 888sport, givemesport (claims 11.1% of basic award = £3.2m).

## CPI
- ONS D7BT page read via WebFetch: annual 2008-2025 and monthly 2008-01 to 2026-08 (latest, released 16 Sep 2026). Monthly averages recomputed match the annual values to rounding (e.g. 2012 monthly mean 96.04 vs published 96.1; 2020 108.75 vs 108.7) - small differences due to monthly rounding. Spot checks re-fetched OK. Not cross-checked against the ONS CSV download (curl blocked).
