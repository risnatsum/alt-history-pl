# Assumptions and judgement calls

Engine-wide entries are numbered E1-xx, E2-xx and so on by the stage that made them.
Scenario entries go under each scenario's heading. "Check" marks anything not yet
confirmed against an official source.

## Engine

### E1: data and real tables

**E1-01 Seasons.** 2008/09 to 2025/26 (the latest finished season at October 2026).
Seasons are labelled by start year in the code (2008 = 2008/09). 2026/27 division
membership is recorded too, so the real moves out of 2025/26 are known.

**E1-02 Sources.** football-data.co.uk is the source of every result (Mus, 13 Oct
2026), using the season CSVs Mus downloaded, committed under
`data/sources/footballdata_csv/`. The one file missing from that download, 2013/14
Premier League, comes from a GitHub copy of football-data
(xgabora/Club-Football-Match-Data). Two independent sources are used only as a check
and to fill any match football-data lacks (none at present): engsoccerdata
(jalapic/engsoccerdata) and openfootball/england. Every source is pinned to a fixed
version in `altpl/config.py`.

**E1-03 Disagreements.** football-data's score is always used. The 291 matches where
another source disagrees are listed in `data/processed/source_conflicts.csv`:
- Portsmouth v Shrewsbury 2012/13: football-data has 2–1; engsoccerdata, openfootball
  and the Wikipedia goal totals point to 3–1 (Check). Using 2–1 changes no points or
  positions, but leaves Portsmouth's goals for and Shrewsbury's goals against one
  lower than Wikipedia's table.
- Boreham Wood v Barrow 2015/16: football-data and engsoccerdata 0–2, openfootball 0–0.
- The other 289 are in League One, League Two and the National League in
  November–December 2025, where openfootball's scores differ from football-data's for
  about 90% of matches. openfootball's fit the bookmaker odds better than real results
  ever do (log-loss 0.95 vs 1.03), the signature of model-generated placeholder scores,
  while football-data's fit as real results do (1.02).

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

**E1-07 Points deductions** (`data/reference/adjustments.csv`, every row cites its
source). Premier League and EFL deductions are checked against dragonfootball.co.uk's
points-deductions list (updated 7 Oct 2026), which Mus supplied, and against the
Wikipedia final tables. National League deductions come from the Wikipedia final
tables (Mus, 13 Oct 2026: no entries from memory); the earlier memory-based list had
several wrong or missing, so all 22 are now taken from those tables. The Wikipedia
check also added Crystal Palace −1 (2008/09 Championship) and Bury −3 (2015/16 League
One), and removed an Aldershot −10 in 2012/13 League Two (their only deduction is the
2013/14 National League one). Two dragonfootball entries are deliberately not applied:
- Bury −12 (2019/20): Bury were expelled before playing, so there is no table to apply it to.
- Brentford −3 (2018/19, "unfulfilled fixture"): Brentford were the side awarded the
  unplayed match at Bolton, all three match sources give a 64-point season, and
  Wikipedia agrees; Mus agrees it is an error on the list (13 Oct 2026).

**E1-07b Check against published tables** (`data/reference/wikipedia_tables/`,
`tests/test_e1.py::test_tables_match_wikipedia`). Every club's position and points in
all 90 tables (2,083 rows) match the Wikipedia final tables. Remaining differences are
goal totals only, none changing points or positions:
- Premier League 2011/12: Wikipedia transcription swapped City and United rows; ours
  has City champions on goal difference, as happened.
- League One 2013/14 Sheffield United: goals against 46 vs 47; Wikipedia's own totals
  don't add up.
- League Two 2012/13 Oxford United: goals ±1; all 46 of our matches agree across 3 sources.
- League One 2012/13 Portsmouth and Shrewsbury: one goal each, from football-data's
  2–1 in their match (E1-03).
- National League 2025/26 Scunthorpe and Wealdstone: goals differ; football-data is the
  only source, probably linked to their abandoned match on 6 Sep 2025 (Check).

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

### E2: ratings model and back-test

**E2-01 Model.** Dixon-Coles Poisson model (`altpl/ratings.py`): one attack and one
defence rating per club per season, a home advantage per season (so 2020/21 without
crowds gets its own) plus a fixed adjustment per division, a shared goal level mu
and the Dixon-Coles low-score correction rho. Fitted to every league match in tiers
1–5, 2008/09–2025/26, at once. The awarded Bolton v Brentford result is left out.
Ratings are constant within a season; form changes inside a season are not modelled.

**E2-02 One scale across divisions.** Divisions never meet within a season, so each
club's ratings are tied to its previous season's in the data by a random walk with
standard deviation sigma per season (wider for a club that left the data and came
back). Clubs moving between divisions (about 4–7 per boundary per season) fix the gap.
Because mu is shared, a rating means the same thing in every division: in E3 a club
playing a division it wasn't really in keeps its real-season rating, with no other
adjustment (but see E2-06). Ratings are shifted so the average PL club-season has
attack 0; strength = attack + defence.

**E2-03 Bookmaker odds.** Average odds across bookmakers (Bet365 where averages are
missing; the football-data GitHub mirror for 2013/14 PL), margin removed by the power
method, which is well calibrated on these matches where scaling all prices equally
leaves a favourite-longshot bias (favourites priced at 64% won 67%). The home-win,
away-win and over-2.5 probabilities are turned into the expected goals they imply
under independent Poissons and added to the likelihood as fractional goals with
weight omega. A held-out match contributes neither its score nor its odds.

**E2-04 Tuning.** sigma = 0.15, chosen by pre-season prediction of 2010/11–2025/26
(flat between 0.1 and 0.25). omega = 16, the smallest weight within 0.0005 log-loss
of the best on 5-fold held-out matches; the odds carry most of the information about
a club's strength once omega passes about 8.

**E2-05 Rating uncertainty.** Standard errors come from the diagonal of the
information matrix counting real results and season links but not the odds (the odds
are not independent observations; counting them made ratings look about
twice as certain as this, and mid-season simulations under-covered real points). With
that, real points fall inside the simulated 5–95% range in 87–90% of club-seasons
mid-season and 87–94% pre-season (target 90%). Simulations draw each club's ratings
from these errors once per run.

**E2-06 Clubs moving up (open question for E3).** Pre-season forecasts of clubs
promoted into the PL over-predicted them by 3.6 points a season on average (48
clubs, standard error 1.6); clubs that stayed in the PL were predicted within 0.3.
Other boundaries show no consistent bias. Part of this is promoted clubs regressing
after a good season, which is not the E3 situation (E3 rates a club from the same
season), so the default is no adjustment; a step-up penalty is a candidate
sensitivity parameter (Check with Mus).

**E2-07 Known limits.** Held-out probabilities are slightly too cautious: favourites
the model gives 64% win 70%, and sharpening every probability by 10% would cut
log-loss by 0.0008. Leicester 2015/16 is rated by what the market thought of them
(they get a 0% title chance when 2015/16 is re-simulated from scratch); with real
results kept as the anchor this matters only for fixtures that never happened. The
held-out model beats the bookmakers' pre-match odds (log-loss 1.016 v 1.026) because
it also knows the rest of the season; it is not a forecast made at the time.

**E2-08 Back-test play-offs (E3 to confirm).** For promotion odds the back-test
simulates the play-offs: two-legged EFL semis (3rd v 6th, 4th v 5th; National League
2v5, 3v4 to 2016/17), a level aggregate settled by a coin flip standing in for extra
time and penalties, and a one-off neutral final. From 2017/18 in the National League,
one-leg eliminators 4v7 and 5v6, then 2nd at home to the lower-placed winner and 3rd
to the other (pairing assumed, Check). 2019/20 League One, League Two and National
League are left out of the season back-tests because they were decided on points per
game.

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
