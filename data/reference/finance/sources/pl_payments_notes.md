# Premier League central payments to clubs, 2008/09 to 2025/26: source notes

File: `pl_payments.csv`. `season` is the start year. Amounts are integer pounds. Every row carries its `source_url`, plus any secondary URLs in `notes`.

## Ground rules and limitations

- The official premierleague.com releases from about 2014/15 onward publish the table only as an **image or PDF**. WebFetch could not read any of these images (pulselive and sportingintelligence image URLs returned fetch errors), and the 2018/19 PDF on S3 now returns AccessDenied. curl to most hosts is blocked by the proxy. As a result, **no row comes directly from an official PL table**. Every row comes from a secondary page that reproduces it, or is derived arithmetically from headline figures stated in text.
- **DERIVED** in `notes` means the value was computed from fetched figures. Examples: merit = stated per-place value x (21 - position); facility = total - equal shares - merit. No number was typed from memory.
- League positions come from the Wikipedia season page for each season, or from the source table's own position column. The URL is given in `notes`.
- The column meaning changes over time:
  - **2019/20 onward:** the published "merit" figure includes an international, position-linked element. In the salarysport tables for 2020/21 to 2024/25, the merit pool is larger than the facility-fee pool, which confirms this. For these seasons, `merit` = UK merit + international merit combined, and `overseas` = the international *equal* share only.
  - **2020/21 to 2024/25:** salarysport publishes only "equal share" = UK equal + international equal + central commercial combined. Its exact value is recorded in `notes` as `equal_combined`. Where a text source splits it, the split is entered rounded to £0.1m, so those rows do not sum exactly to `total`. The exact `total` should be trusted over the components.

## Coverage summary

| Season | Status | Main source |
|---|---|---|
| 2008/09 | **MISSING**. No per-club or headline figures found | none |
| 2009/10 | PARTIAL: position, merit (derived), rounded equal/overseas; 3 totals | sportingintelligence (SI) substack |
| 2010/11 | PARTIAL: position, merit (derived), equal/overseas to £10k; 2 totals | SI |
| 2011/12 | PARTIAL: position, merit (derived), exact equal/overseas; 6 totals (3 exact) | SI |
| 2012/13 | PARTIAL: position, merit (derived), exact equal/overseas; 5 totals (2 exact) | SI |
| 2013/14 | COMPLETE: exact totals; facility derived as residual | futbolekonomi table + SI components |
| 2014/15 | PARTIAL: position, merit (derived); 5 totals (2 exact); 2 facility fees | SI, sportbusiness, others |
| 2015/16 | COMPLETE: exact totals; commercial and facility derived | Sky Sports totals + SI + sportbusiness |
| 2016/17 | COMPLETE: exact; equal and facility split derived from SI anchors | Sky Sports full table |
| 2017/18 | COMPLETE: 5 exact totals; other 15 derived to about ±£2; CityAM full table at £0.01m | CityAM + sportbusiness + SI |
| 2018/19 | COMPLETE and exact | salarysport + fanbanter (split) |
| 2019/20 | **ESTIMATES ONLY** (no official table found) | Planet Football (Swiss Ramble estimates) |
| 2020/21 | Totals, facility and merit exact; equal split NOT found (equal/overseas/commercial blank) | salarysport |
| 2021/22 | Totals, facility and merit exact; equal split rounded | salarysport + pinkun |
| 2022/23 | Totals, facility and merit exact; equal split rounded | salarysport + football365 |
| 2023/24 | All at £0.1m precision (salarysport); split rounded | salarysport + football365 |
| 2024/25 | All at £0.1m precision; split rounded | salarysport |
| 2025/26 | **ESTIMATES ONLY**. PL had not published by 13 Oct 2026 | softfootball / football365 (The Athletic estimates) |

## Per-season detail

### 2008/09
Nothing found. Searches for a per-club table, the merit value per place and totals returned nothing. The SI series starts with 2009/10. The positions were fetched (Wikipedia 2008-09 page) but are not used, because there are no money figures to attach to them. **No rows are written for this season.**

### 2009/10
- Source: https://sportingintelligence832.substack.com/p/the-premier-league-where-the-money-went-in-2009-10 (the table is an image, `PL-payments-2009-10.jpg`).
- Text figures:
  - Merit £800,424 per place. Chelsea received £16,008,480 = 20 x 800,424, which checks.
  - Domestic equal share £14.6m; foreign equal share £10.1m (both rounded).
  - Facility fees for 10 to 24 live games.
  - Totals: Man Utd £52.996m, Chelsea £52.8m, Portsmouth £31.8m.
- Headline: parachute £12.4m each to five clubs. Projected: from 2010-11, parachutes of £16m a year for 2 years, then £8m a year for 2 years.
- Gaps: facility fees, commercial, and 17 of 20 totals.

### 2010/11
- Source: https://sportingintelligence832.substack.com/p/where-the-money-went-premier-league-prize-and-tv-payments-for-2010-11-240503 (table is an image).
- Text figures:
  - Merit £756,756 per place; Man Utd merit £15,135,120.
  - Domestic equal £13.82m; foreign equal £17.93m.
  - Facility fee £485,000 per live UK match, 10 to 26 matches. Live counts per club were not found, so facility was not derived.
  - Totals: Man Utd £60,429,052; Blackpool £39,080,036.
- Headline: top-to-bottom ratio 1.55; overseas rights 2010-13 £1.437bn.
- Gaps: facility, commercial, and 18 totals.

### 2011/12
- Source: https://sportingintelligence832.substack.com/p/where-the-money-went-premier-league-prize-and-tv-payments-for-2011-12-150501, plus the Q&A page https://www.sportingintelligence.com/2012/06/19/premier-league-tv-rights-qa-including-where-the-money-goes-and-what-next-190601/
- Text figures:
  - Merit £755,062 per place.
  - Domestic equal £13,788,093; foreign equal £18,764,644.
  - Facility £485,000 per live match.
  - Totals: City £60,602,289; Utd £60,325,337; Wolves £39,084,461; Newcastle £54.2m; Villa about £42m; Arsenal £56.2m (Q&A page).
- Headline: club pot £1.055bn, of which £968.2m went to the 20 PL clubs and the rest to 7 parachute clubs. Parachute £15,475,005 each to Birmingham, Blackpool and West Ham. Commercial sharing "roughly £2.5m per club" (approximate, not entered).
- The facility fee **does not** reduce to £485k x games plus a constant, based on the City and Wolves totals, so facility was not derived.
- Gaps: facility, commercial, and 14 totals.

### 2012/13
- Source: https://www.sportingintelligence.com/2013/05/21/where-the-money-went-premier-league-prize-and-tv-payments-for-2012-13-210501/ (table images `PL-cash-12-13.jpg` and `PL-document-TV-12-13.jpg`).
- Text figures:
  - Merit £755,881 per place.
  - Domestic equal £13,803,038; foreign equal £18,931,726.
  - Totals: Man Utd £60,813,999; City £58.1m; Arsenal £57.1m; Spurs £55.9m; QPR £39,752,462.
  - Live games: Utd 25; Arsenal and Liverpool 22; City and Spurs 21; Chelsea 16.
- Headline: ratio 1.53; parachutes £5.7m to £15.7m across 8 former clubs; overseas 2013-16 sold for more than £2bn.
- Gaps: facility, commercial, and 15 totals.

### 2013/14
- Totals: https://futbolekonomi.com/index.php/economy/3085-manchester-city-earn-p965m-for-successful-premier-league-season.html. All 20 totals are given, and they sum exactly to the stated £1,563,117,350. In that table "Position" means payment rank, not league position.
- Components from https://sportingintelligence832.substack.com/p/where-the-money-went-liverpool-top-premier-league-prize-cash-in-2013-14-140501:
  - Equal £52,198,111 = domestic £21,631,444 + overseas £26,295,817 + commercial £4,270,850.
  - Merit £1,236,083 per place.
- Facility is derived as the residual. Checks: Liverpool £21,860,648 against SI's "£21.9m from 28 games"; Cardiff £8,648,108 against SI's "minimum £8.6m".
- Headline: ratio 1.57. Parachutes are not stated.

### 2014/15
- Source: https://sportingintelligence832.substack.com/p/where-the-money-went-chelsea-top-premier-league-cash-table-with-99m-prize-020601 (table image). The official season review page (http://review.premierleague.com/2014-15/the-premier-league/payments-to-premier-league-clubs.html) links to the table but does not contain it.
- Text figures:
  - Merit £1,244,898 per place; minimum facility £8,775,160.
  - Chelsea £98,999,554 (merit £24.9m, facility £19.98m, domestic "nearly £22m", overseas £27.8m, commercial £4.4m).
  - City £98.5m; Utd £96.8m (facility £21.5m, 27 games, per calcalist); Arsenal £96.5m.
  - QPR £64,886,028 (sportbusiness). SI says £64.9m.
  - Sportskeeda says overseas was £27.5m per club, which conflicts with SI's £27.8m. Equal shares were therefore left blank.
- Headline: ratio 1.53. Parachutes: Cardiff, Fulham and Norwich £25m each; Reading and Wigan £20m each. Total pool about £1.6bn. Solidarity rule (SI): Championship clubs get 30% of a year-3 parachute payment, League One 4.5%, League Two 3%.
- Gaps: 15 totals, 18 facility fees, and exact equal/overseas/commercial.

### 2015/16
- Totals: Sky Sports https://www.skysports.com/football/news/11712/10293524/champions-leicester-only-fifth-highest-earning-club-in-premier-league. All 20 are given and sum to £1,638,805,918, which matches Sky and fcbusiness.
- Components:
  - SI: combined equal £55,849,800; merit £1,242,405 per place.
  - sportbusiness: domestic equal £21,924,800; overseas £29,415,848.
  - Commercial = £4,509,152, derived; Sky gives £4.5m.
- Facility residual check: Arsenal £21,496,762, exactly the figure SI states.
- Headline: ratio 1.5153; minimum facility £8,782,088; Leicester merit £24,848,100. Parachutes £25,937,356 each to Burnley, Hull and QPR. Total paid out £1.81bn (prize money £1.64bn + parachutes £172m, per SI). Wikipedia's parachute total for 2015-16 is £171.8m.

### 2016/17
- Sky Sports full table: https://skysports.com/football/news/11668/10900647/chelsea-lead-premier-league-payments-with-150-8m. It has UK live, domestic TV (combined), overseas £39,090,596, commercial £4,759,404 and total. Every row sums to its total.
- League totals:
  - domestic £1,521,515,773
  - overseas £781,811,920
  - commercial £95,188,080
  - total £2,398,515,773
- Split of domestic, from SI anchors (https://sportingintelligence832.substack.com/p/where-the-money-went-chelsea-top-prize-cash-table-with-151m-310501):
  - Chelsea merit £38,832,180; Chelsea facility £32,827,014 (28 games); minimum facility £12,377,522; merit £1,941,609 per place.
  - These give an equal share of £35,301,989. Sky and football365 text both say £35.3m.
- Parachutes (Sky table), total £219,117,013:
  - Aston Villa, Newcastle and Norwich £40,915,922 each
  - QPR £31,176,663
  - Cardiff, Fulham, Reading and Wigan £16,298,146 each
- Headline: ratio 1.6135 (SI).

### 2017/18
- CityAM full table with all components at £0.01m: https://cityam.com/?p=2064110. Every row sums to its total except Newcastle, where the facility figure is a typo (prints £21.25m; the correct figure is £21.35m).
- Exact anchors (sportbusiness https://media.sportbusiness.com/news/manchester-united-finishes-top-of-premier-league-payment-table, and SI):
  - Equal £34,812,558; international £40,771,108; commercial £4,838,892.
  - Merit £1,931,268 per place.
  - City facility £30,390,736 (26 games); Utd facility £32,650,495 (28 games).
  - Exact totals: City £149,438,654; Utd £149,767,145; Liverpool £145,904,609; Spurs £144,446,238; WBA £94,666,492.
- Facility for the other 15 clubs = £12,312,666 + about £1,129,879.4 per game above 10, derived. All derived totals agree with CityAM's £0.01m totals.
- Planet Football (https://www.planetfootball.com/quick-reads/club-by-club-a-breakdown-of-the-2017-18-premier-league-prize-money) has different live counts for Burnley (7) and Huddersfield (9). CityAM's counts were used.
- Headline: total about £2.42bn (derived sum £2,419,583,752). Parachutes "almost £243m" to 8 clubs: Sunderland, Hull and Middlesbrough £41.57m each; Villa and Norwich £34m; Cardiff, Fulham and QPR £16.6m. Wikipedia total £242.6m. Solidarity "£100m split amongst the remaining 64 clubs" (Wikipedia, https://en.wikipedia.org/wiki/Premier_League_parachute_and_solidarity_payments). The PL release page also says £100m per season in solidarity plus youth grants.

### 2018/19
- salarysport table (https://salarysport.com/football/premier-league/prize-money/). It is exact and every row sums.
- Split from fanbanter (https://fanbanter.co.uk/how-much-every-2018-19-premier-league-club-were-paid/): UK equal £34,361,519; international £43,184,608; commercial £4,965,392.
- League totals: equal £687,230,380; facility £402,889,186; merit £402,888,780; international £863,692,160; commercial £99,307,840; **total £2,456,008,346**. This equals the salarysport sum.
- Headline: Wikipedia parachute total £265.2m. EFL solidarity 2018-19 £106.3m (Championship £4.65m per club / £79.1m; League One £0.70m / £16.1m; League Two £0.47m / £11.2m). The PL page says "more than £140 million per season in Solidarity Payments and ringfenced Youth Development grants".

### 2019/20
- **No official release found.** salarysport says it holds no 2019/20 table. Rows are **estimates** from Planet Football / Swiss Ramble (https://www.planetfootball.com/quick-reads/club-by-club-a-breakdown-of-the-2019-20-premier-league-prize-money) at £0.1m precision.
- Their overseas column varies by position (£44.6m to £71.3m). The estimates appear to exclude the COVID broadcaster rebates, which sportbusiness puts at about £330m in total (£223m domestic, £107m international, per The Athletic).
- Headline: Wikipedia parachute estimate £240.0m.

### 2020/21
- salarysport exact table. Pools: equal £1.70bn; facility £367.1m; merit £454.5m; total £2,518,439,820.
- Merit is £2,164,350 per place. Because the merit pool exceeds the facility pool, merit includes an international element.
- **The split of equal_combined (£84,841,528) into UK/international/commercial was not found.** Those columns are blank.
- The PL release (https://premierleague.com/news/2222377) holds the table only as an image. Planet Football said at the time that the PL "has not revealed the official prize money figures" and printed estimates, which differ from salarysport (for example West Ham live 22 vs 24). salarysport was used.
- Headline: Wikipedia parachute estimate £232.0m.

### 2021/22
- salarysport exact table: equal_combined £87,509,969; merit £2,057,220 per place (combined); total £2,536,897,040.
- Split (pinkun, rounded): UK £31.8m / international £48.9m / commercial £6.8m.
- Headline: Wikipedia parachute estimate £185.6m.

### 2022/23
- salarysport exact table: equal_combined £88,605,889; merit £3,113,491 per place (combined); total £2,781,002,165.
- Split (football365, rounded): UK £31.2m / international £48.0m / commercial £9.4m.
- The UK vs international merit split is not published in text. The Athletic estimate via Planet Football implies about £1.69m UK + £1.425m international per place (City £33.8m + £28.5m = £62.3m).
- Headline: Wikipedia parachute estimate £177.0m.

### 2023/24
- salarysport, £0.1m precision: equal_combined £95.1m; totals sum £2,848.4m.
- Split (football365): UK £31.2m / international £55.7m / commercial £8.2m.
- Matchday Finance (https://www.matchdayfinance.com/post/premier-league-broadcast-distribution-for-season-2023-24): total £2.848bn = domestic £1.333bn + international £1.351bn + commercial £164m. Merit about £2.8m per place; facility about £0.9m per game.

### 2024/25
- salarysport, £0.1m precision: equal_combined £96.9m = UK £29.8m + international £59.2m + commercial £7.9m.
- Pools: UK equal £596m; facility £339m; UK merit £339m; international equal £1.18bn; international merit £218m; commercial £158m; total £2.83bn.
- Per-club UK/international merit can be approximated as pool x (21 - pos)/210. The salarysport Liverpool page shows UK merit £32m and international merit £21m.
- The official PL page (https://www.premierleague.com/en/news/4325409/premier-league-central-payments-to-clubs-202425-season) is image-only. It says the PL committed more than £550m to the wider game in 2024/25.
- SI (si.com) lists the same totals.

### 2025/26
- **Estimates only.** Football365 (13 Oct 2026, https://www.football365.com/news/premier-league-prize-money-table-2026-27) says the PL has "yet to" publish.
- Totals are The Athletic estimates via softfootball. Equal shares £99.9m = UK £31.9m + international £56.5m + commercial £11.5m (football365; SI says international is £56.6m). Merit is £3.76m per place.
- Facility is derived. Check: Arsenal £23.6m, which matches football365.
- Brentford is £161.6m in softfootball but £161.5m in premierleaguenow.

## Checks run
- 2013, 2015, 2016 and 2018: the 20 totals sum exactly to the stated league totals.
- Every row whose components are all exact sums to `total` within £1.
- The 2017/18 derived figures match CityAM's rounded components to within £0.01m, except the CityAM Newcastle facility typo noted above.
- 2021/22 and 2022/23 rows do not sum exactly, because the split components are rounded to £0.1m.
