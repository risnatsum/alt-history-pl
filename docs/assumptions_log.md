# Assumptions and judgement calls

Engine-wide entries are numbered E1-xx, E2-xx and so on by the stage that made them.
Scenario entries go under each scenario's heading. "Check" marks anything not yet
confirmed against an official source.

## Engine

### E1: data and real tables

**E1-01 Seasons.** 2008/09 to 2025/26 (the latest finished season at October 2026).
Seasons are labelled by start year in the code (2008 = 2008/09). 2026/27 division
membership is recorded too, so the real moves out of 2025/26 are known.

**E1-02 Sources.** Three independent sources, reconciled match by match:
football-data.co.uk (season CSVs downloaded by Mus, committed under
`data/sources/footballdata_csv/`), engsoccerdata (jalapic/engsoccerdata, to 2024/25,
missing 2022/23 for tiers 1–4) and openfootball/england (National League only from
2015/16). A GitHub mirror of football-data (xgabora/Club-Football-Match-Data) is used
only for the odds of 2013/14 Premier League, the one file missing from Mus's download;
it does not vote on scores because it is a copy of football-data. Every source is
pinned to a fixed version in `altpl/config.py`.

**E1-03 Settling disagreements.** Where sources disagree the majority wins; on a
two-way split football-data wins. All 291 disagreements are listed in
`data/processed/source_conflicts.csv`. Two are genuine one-offs (Portsmouth v
Shrewsbury 2012/13, Boreham Wood v Barrow 2015/16) settled by majority. The other 289
are all in League One, League Two and the National League in November–December 2025,
where openfootball's scores differ from football-data's for about 90% of matches.
Football-data was kept: its scores fit the bookmaker odds about as well as real
results do elsewhere (log-loss 1.02 vs 1.03 for matches where the sources agree),
while openfootball's fit them better than real results ever do (0.95), the signature
of placeholder scores generated from a model rather than recorded. So 2025/26 League
One, League Two and National League rest on football-data alone for those months.

**E1-04 Club identity.** Each club has one `club_id` across sources and seasons
(`data/reference/clubs.csv`). Chester City (expelled 2010, wound up) and the phoenix
Chester FC are different clubs; sources call both "Chester" and the season decides.
FC Halifax Town is the only Halifax in range (the old club folded in 2008).

**E1-05 Ranking.** Points, then goal difference, then goals scored. One tie survives
that in the whole dataset: Oldham and Tranmere in 2010/11 League One (17th/18th, same
points, GD and goals); it doesn't affect any promotion or relegation, so it is left in
alphabetical order (Check).

**E1-06 2019/20.** The Premier League and Championship finished their fixtures.
League One, League Two and the National League were curtailed and decided on
unweighted points per game, with deductions taken off before dividing. Ties on PPG go
to goal difference, then goals scored.

**E1-07 Points deductions** (`data/reference/adjustments.csv`). Premier League and EFL
deductions are checked against dragonfootball.co.uk's points-deductions list (updated
7 Oct 2026), which Mus supplied; all 37 that apply to a table match it. Checking added
four the first draft missed (Aldershot −10 in 2012/13 League Two, Morecambe −3 in
2023/24, Sheffield United −2 in 2024/25, West Brom −2 in 2025/26) and corrected
Reading 2023/24 from −4 to −6. Two entries on that list are deliberately not applied:
- Bury −12 (2019/20): Bury were expelled before playing, so there is no table to apply it to.
- Brentford −3 (2018/19, "unfulfilled fixture"): Brentford were the side awarded the
  unplayed match at Bolton, and all three match sources give a 64-point season, so this
  looks like an error on the list (Check).
National League deductions aren't on that list and remain from memory (Check):
Salisbury City −10 (2009/10), Kidderminster −5 (2010/11), Darlington −10 (2011/12),
Aldershot −10 (2013/14; possibly the same penalty as their 2012/13 League Two one,
counted twice), Dover −12 (2021/22) and Southend −10 (2023/24). Any National League
deduction that changed no promotion or relegation could also be missing.

**E1-08 Expunged and expelled clubs.** Chester City 2009/10 and Dover Athletic 2020/21
had their records expunged: their matches are removed from the tables (football-data
still lists Dover's) but they count as members of the division that season. Bury were
expelled before 2019/20, so League One had 23 clubs.

**E1-09 Moves that didn't follow the table** (`data/reference/movement_exceptions.csv`):
Salisbury City demoted 2010 (Forest Green reprieved), Rushden & Diamonds expelled
2011, Hereford United and Salisbury City expelled 2014 (Chester and Dartford
reprieved), Bury promoted then expelled 2019, Gateshead demoted 2019 (Aldershot
reprieved), only one club relegated from League Two in 2019/20 (Stevenage stayed up),
Macclesfield relegated then wound up in 2020, no relegation from the National League
in 2020/21.

**E1-10 League structure** (`data/reference/seasons.csv`): automatic promotion places,
play-off places and relegation places for each season and division, as they really
were. The National League play-offs differ from the EFL's: two-legged semi-finals to
2016/17, then from 2017/18 six clubs with one-leg eliminators and semi-finals. The
simulator (E3) will follow these real formats rather than the generic "two-legged
semi-finals" of the spec.

**E1-11 Awarded result.** Bolton 0–1 Brentford (2018/19 Championship) was not played
and was awarded; it counts in the table but is flagged (`awarded`) so the ratings model
can leave it out.

**E1-12 Odds.** Kept for E2 in `data/sources/footballdata.csv`: Bet365, Pinnacle
(from 2012/13, closing prices later), market maximum and average 1X2, and average
over/under 2.5. football-data renamed its maximum/average columns in 2019/20; both
names are mapped to one.

## Scenario S01: Man City removed

Not started (S1 comes after the engine). Data notes from E1:
- 1A: Sheffield United were the best-placed club not promoted from the 2008/09
  Championship (3rd, 80 pts, lost the play-off final to Burnley), ahead of Reading
  (4th, 77). So 1A promotes Sheffield United, as the brief expected.
- 1B and 1C need divisions with an odd number of clubs (19 in the PL, 21 in the
  Championship), so one club is idle each round. That is an engine requirement for E3;
  E1's data handles any division size.
- In every variant, City's real 2009/10+ results are dropped and the rest of each
  season's real results stay as the anchor.
