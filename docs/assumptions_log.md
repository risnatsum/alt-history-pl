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
to the other (pairing assumed, Check; E3-03 found a fixed bracket instead and the
E3 simulator uses that). 2019/20 League One, League Two and National
League are left out of the season back-tests because they were decided on points per
game.

### E3: season simulator

**E3-01 How a run works** (`altpl/simulator.py`). Each run plays every division of a
season, then carries its own promotions and relegations into the next, so membership
can differ between runs. A division can have any number of clubs: with an odd number
every club still plays everyone home and away (2(n-1) matches), one club sitting out
each round; rounds and fixture dates are not modelled. A scenario changes only the
`World` (clubs removed, division sizes, promotion and relegation places), never the
code. Default 10,000 runs with a fixed seed (20083).

**E3-02 Real results as the anchor.** A fixture keeps its real score when the same two
clubs really met, home and away the same way round, in the same division and season;
anything else is simulated. `anchored=False` simulates everything, as the check the spec
asks for. Play-offs: if a run's whole play-off field (every club in the same seed) is
the real one, the real winner goes up; otherwise any individual tie that really
happened keeps its real winner where engsoccerdata has it (EFL 2008/09-2015/16,
National League 2012/13-2018/19), and the rest are simulated. Real play-off ties after
those years are not in any source the build can read, so only whole-field matches
reproduce them.

**E3-03 Play-off formats** (`data/reference/seasons.csv`). EFL: 3rd v 6th and 4th v
5th over two legs, the higher seed at home in the second leg, then a one-off final on
neutral ground. Checked against every real EFL semi-final 2008/09-2015/16 in
engsoccerdata; later seasons assumed the same (Check). No away-goals rule: level
aggregates went to extra time and penalties even when one side had more away goals
(Leicester v Cardiff 2009/10, Bournemouth v Huddersfield 2010/11 and Swindon v
Brentford 2012/13 in engsoccerdata). A level tie gets extra time, simulated as a third
of a match at the same scoring rates, then penalties as a coin flip. National League to
2016/17: 2nd v 5th and 3rd v 4th over two legs (checked 2012/13-2015/16). From
2017/18: one-leg eliminators 4th v 7th and 5th v 6th, then 2nd at home to the 5th/6th
winner and 3rd at home to the 4th/7th winner, no re-seeding. Real ties fix this: in
2018/19 2nd (Solihull) met 5th (Fylde) while 3rd (Salford) met 7th (Eastleigh), from
engsoccerdata; in 2024/25 2nd (York) met 5th (Oldham) and 3rd (Forest Green) met 7th
(Southend), from gloverscast.co.uk's round-up; 2025/26 2nd (Rochdale) met 5th
(Scunthorpe) and 3rd (Carlisle) met 4th (Boreham Wood), from Sky Sports and the
Wikipedia final page. A Sports Illustrated preview of 2025/26 described the opposite
pairing; the real ties are used. This replaces the re-seeded pairing assumed in E2-08.

**E3-04 Clubs in a division they weren't really in** keep their real-season rating with
no adjustment (Mus, 14 Oct 2026, on E2-06). Two sensitivities, both off by default, in
strength units (attack + defence, split equally): `step_up`, a penalty per division a
club plays above its real one; `money_boost`, a lift for a club promoted in the run but
not in reality (its real rating already carries any real promotion). A club with no
real rating that season (outside the pyramid in reality, e.g. relegated from the
National League in reality but not in the run) carries its nearest real season's
rating, its uncertainty widened by sigma per season of distance (Check: probably
generous to clubs that really dropped out).

**E3-05 Moves between seasons.** Automatic places and play-off winners go up. Each
division is then filled to its real size for next season from the top down, so
normally the real number of clubs go down. Real departures (expelled, demoted, wound
up, expunged and not continuing) apply to the club wherever it is in the run, and the
division it leaves relegates one fewer: the best-placed club in the drop zone is
reprieved, as Forest Green, Chester, Dartford and Aldershot really were. A demoted club
leaves the modelled pyramid wherever it is (Check: only National League demotions
exist in the data). Bury (expelled August 2019) and Macclesfield (wound up September
2020) left too late to be replaced: their vacancy follows the club, so in a run where
Bury were not promoted, League Two rather than League One runs one club short in
2019/20 (column `vacancy` in `movement_exceptions.csv`). Clubs entering the National
League from below are the clubs really promoted into it; a club relegated out of the
National League in a run but not in reality stays outside the model unless it is a
real entrant later (step 6 is not simulated; Check). If a division is still short after
relegating nobody, the next-best club below is promoted.

**E3-06 Clubs a scenario removes.** By default their place is filled by cascade: the
best club not promoted from the division below goes up, then the best not promoted
from the division below that, down to the National League, which relegates one fewer.
From the real 2008/09 tables, removing Manchester City from 2009/10 promotes Sheffield
United, Milton Keynes Dons, Bury and Cambridge United one division each and reprieves
Woking (`tests/test_e3.py`). `removal_fill="reprieve"` keeps the removed club's
division one relegation short instead.

**E3-07 Deductions and expunged records** follow the club into whichever division it is
in. An expunged club's matches count for nobody and it finishes bottom.

**E3-08 Ties in the table** after points (or points per game), goal difference and
goals scored are settled by a random draw. Real tie-breaks (head-to-head and so on)
are not modelled; E1 found one exact tie in the real data (E1-05).

**E3-09 2019/20 curtailed divisions** (League One, League Two, National League). A
pairing of two clubs really in the division counts only if it was really played before
the stop; any other pairing counts with the division's real share of matches played.
Tables rank on points per game, as in E1-06.

**E3-10 What the tests show** (`docs/e3_validation.md`). With every real result kept,
every run reproduces all 2,083 real club-seasons and every real promotion, relegation,
expulsion and reprieve. Fully simulated seasons are cautious (more real points inside
the 5-95% range than the 90% they should), as E2's in-sample back-test found; with a
fifth of fixtures hidden and simulated, the scenario situation, ranges and chances are
close to right. See the report for the numbers.

**E3-11 European places** were not in the engine at E3. E4 added the sourced allocation
(E4-07); PL tables now show each club's chance of a league-earned Champions League,
Europa League and Conference League place, as well as top-4 to top-7.

**E3-12 Last season simulated.** Moves out of the last season use its nominal
promotion and relegation places, because next season's division sizes are not set.

### E4: finance model

**E4-01 Difference, not level.** Each run's revenue is priced with the same model as
reality's, and only the difference is reported, so errors in revenue levels (which
the model does not try to get right for each club) cancel. A club's revenue is the
sum of the components below; other income (player sales, cup runs, loans, owner
funding) is the same in a scenario as in reality and left out. Revenue counts only
inside the simulated seasons: money a run's last season would earn the season after
(parachutes, UEFA prize money) is not counted.

**E4-02 Sources, and no figure from memory.** Every figure is in
`data/reference/finance/sources/` with the URL it was read from. The network allows
only GitHub and PyPI, so pages were read through a web-reading tool that summarises
them; read the figures as transcriptions (Check). No official PL payment table could
be read (they are images); PL payments come from pages that reproduce them
(sportingintelligence, Sky Sports, CityAM, futbolekonomi, salarysport, fanbanter,
Planet Football). Each price carries a status: sourced, derived (arithmetic on
sourced figures), estimate (a source's own estimate) or filled (no source; stated
rule), listed per item and season in `docs/e4_validation.md`.

**E4-03 Fill rules.** A season with no sourced value takes linear interpolation
between the nearest sourced seasons, or the nearest season's value at the ends,
unless a better rule is stated: 2008/09 PL payments and parachutes take 2009/10's
(same 2007-10 TV contract; nothing was found for 2008/09); missing years 2-4 of the
2011/12-2013/14 parachutes follow the TV deal's scheme shape (16/16/8/8, then
23/18/9/9, Swiss Ramble); 2025/26 parachute year 3 = 20/55 of year 1. Thinnest
items: the EFL's own distribution in League One and Two (one or two sourced
seasons), and League One/Two solidarity before 2018/19.

**E4-04 PL central payments by position.** Per season: a base payment (the average
club's sourced total less its average merit), merit of one unit per place above
21st (the median step between sourced merit payments; from 2019/20 this includes the
overseas merit element), and facility fees as a straight line in position (fitted on
the clubs' sourced fees). Facility fees really follow TV picks, so a club's real
payment differs from its position's by £2-4m a season (validation §4). 2019/20 and
2025/26 rest on journalists' estimates; 2009/10-2012/13 and 2014/15 bases on the few
clubs whose totals were found (2014/15 interpolated, as four of its five sourced
clubs were top-four clubs). Positions beyond 20 in a bigger PL earn no merit; a
smaller PL keeps the same scale.

**E4-05 Parachutes** are paid while the club is outside the PL, by the rules of the
season it went down and the amounts of the season paid: two years for clubs relegated
up to 2007/08; three for 2008/09 relegations; four for 2009/10 to 2014/15; from
2015/16 relegations, three years, or two after a single PL season (Sky Sports, June
2015; Evans/CSB; Wikipedia). The 2008/09-three-years and 2009/10-four-years cut-offs
are read from the recipient counts by season (Evans Table 1; sportingintelligence's
5, 7 and 8 recipients in 2009/10, 2011/12 and 2012/13, all reproduced). PL membership
from 2000/01 (engsoccerdata) sets who is on a parachute in 2008/09. 2012/13's stated
range (£5.7m-£15.7m) is read as years 4 and 1. A blog's 2023/24 figures (~£44m/£36m/
£16m) sit below both neighbouring seasons and were replaced by the mean of 2022/23
and 2024/25. 2019/20-2021/22 are Wikipedia's own estimates. The EFL's own small
parachutes (2016/17 on) are left out.

**E4-06 Solidarity and EFL money.** Championship clubs on a parachute get no
solidarity; every League One and League Two club does. Set aside: one club's League
One accounts line for 2009/10 (£0.1m, below the next season's League Two figure) and
an ambiguous £1.0m EFL distribution for 2010/11 between £2.47m and £2.5m. National
League clubs get no central money in the model (only a 2024/25 total was found, from
a secondary source), so moves between League Two and the National League are priced
by matchday and commercial revenue alone.

**E4-07 UEFA places and money.** The competition each PL position earned through the
league each season is as it really happened (Wikipedia season articles): places a cup
winner left to the next league position count as league places; places won through a
cup, the fair-play places and title-holders' places do not, since the same club
qualifies the same way in a scenario and in reality, so they cancel (Check: a scenario
that changes a cup winner's league finish is not handled). Prize money for a place is
the average of English clubs' UEFA payments in that competition the following season
(UEFA distribution documents and financial reports), at the season's average euro
rate (ECB reference rate via the Bundesbank). The stage reached is not modelled.
Missing: 2020/21 Europa League, 2021/22 and 2023/24 (only rounded press figures for
some clubs), 2025/26 (not yet published); Conference League rests on two winners'
payments, so it overstates a typical entrant.

**E4-08 Matchday and commercial revenue per division.** From clubs' accounts in the
season before and after a move (Swiss Ramble, Price of Football, club reports;
Covid seasons 2019/20 and 2020/21 left out): PL v Championship from 30 moves, pooled
over promotions and relegations, a straight-line trend in real terms (about £5.5m a
season in 2008/09 rising to £12.6m in 2025/26, nominal); Championship v League One
from 4 promotions, constant in real terms (about £3-5m). League One v League Two and
League Two v National League: no usable accounts, so each step is the one above times
the ratio of League Two to League One average revenue (0.64, Deloitte); Check. The
same accounts feed the promotion test (§5), though this component is a small part of
each change. Relegated clubs lose less than promoted clubs gain (validation §5 shows
a small bias); the pooled figure sits between them.

**E4-09 Money in 2025/26 pounds** uses the ONS CPI (D7BT), averaged August-May of each
season.

**E4-10 What the tests show** (`docs/e4_validation.md`). Reality reproduced: a
difference of exactly £0 for every club-season. Parachute recipients match every
sourced list and count. Real promotions from the Championship outside the Covid
seasons: the model's change in revenue is within 10% of the published accounts for
most clubs, with little bias; relegations slightly overstate the loss. The Covid
seasons and the lower divisions are much less certain.

## Scenario S01: Man City removed

Not started (S1 comes after the engine). Data notes from E1:
- 1A: Sheffield United were the best-placed club not promoted from the 2008/09
  Championship (3rd, 80 pts, lost the play-off final to Burnley), ahead of Reading
  (4th, 77). So 1A promotes Sheffield United, as the brief expected.
- 1B and 1C need divisions with an odd number of clubs (19 in the PL, 21 in the
  Championship), so one club is idle each round. The E3 simulator handles any division
  size (E3-01) and fills a removed club's place by cascade by default (E3-06).
- In every variant, City's real 2009/10+ results are dropped and the rest of each
  season's real results stay as the anchor.
