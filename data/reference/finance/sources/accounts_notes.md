# Club and divisional revenue: notes, gaps, doubts

Gathered 14 Oct 2026. Every figure in the two CSVs comes from a page fetched in this session, and its URL is in `source_url`. Nothing was entered from memory. Values marked DERIVED or IMPLIED in `notes` are arithmetic on stated figures, for example a total minus two streams, or a prior year worked back from a stated change. ESTIMATE means the source itself said the figure was an estimate (Swiss Ramble did this when a club gave no breakdown). Amounts are in pounds as integers. The precision is whatever the source used, usually £0.1m or £1m.

## Conventions
- `season` = the year the season starts (2015 = 2015/16). For a club, it is the season the accounts mainly cover.
- `year_end` is filled only when a fetched source stated it. Most rows have it blank.
- Stream definitions follow the source. Swiss Ramble uses matchday / broadcasting / commercial, with catering and retail in commercial. Some news sources give only "gate receipts" or "sponsorship", and the notes say so. For Norwich 2018–19 I mapped the club's own turnover note: gate = matchday, FA & League plus media = broadcasting, everything else = commercial.
- Broadcasting in the Championship includes parachute payments where the club received them. That is why relegated clubs show £40–68m of broadcasting.
- A few club-seasons have two rows from different sources (for example Middlesbrough 2016/17, Cardiff 2017/18–2018/19 in the notes). The differences are small, from definitions or rounding.

## Coverage of club_revenue.csv (179 rows, 36 clubs, 110 rows with a full split)
**Promotions to the Premier League, 2009–2024 (48 promotions).** Both the last Championship season and the first PL season have a full split for 22 promotions: Cardiff 13, Hull 13, Palace 13, Burnley 14, QPR 14, Norwich 15, Wolves 18, Norwich 19, Villa 19, WBA 20, Fulham 20, Watford 21, Brentford 21, Fulham 22, Bournemouth 22, Forest 22, Burnley 23, Sheffield Utd 23, Luton 23, Leicester 24, Ipswich 24, Southampton 24, plus near-full cases (Leicester 14, Leeds 20, Fulham 18, Burnley 16) where one stream is missing or derived. 2009–2012 and 2015–2018 mostly have totals only.

**First season after relegation.** A split is available for: Burnley 2010 (total only), Blackpool 2011 (total), West Ham 2011, Birmingham 2011 (total plus commercial), Wolves 2012, QPR 2013, Norwich 2014, Burnley 2015 (partly derived), Newcastle 2016 (total), Villa 2016, Middlesbrough 2017, Sunderland 2017, Hull 2017 (partly derived), WBA 2018, Fulham 2019, Bournemouth 2020, Watford 2020, Fulham 2021, Sheffield Utd 2021, WBA 2021, Burnley 2022, Norwich 2022, Watford 2022, Leicester 2023, Leeds 2023 and Southampton 2023.

**Biggest gaps (no usable figure or no split):**
- Reading 2011/12 and 2012/13: nothing (only Reading 2010/11 and 2007/08).
- Watford 2014/15 and 2015/16: nothing in GBP. Watford 2016/17 was £123.9m, "up almost £30 million". Calcio e Finanza gives €119.7m for 2015/16 including player-sale profits, which was not used.
- Hull 2015/16, and Norwich 2020/21 (the Championship season before the 2021 promotion): nothing found.
- Splits are missing for 2008/09–2011/12 for Wolves, Birmingham, Burnley, Newcastle, Blackpool, Norwich and Swansea, and for 2016/17–2018/19 for Newcastle, Brighton, Huddersfield, Cardiff and Sheffield Utd. Totals are present for most of these.
- Burnley 2008/09: no figure.
- Blackpool 2009/10 = £9m comes from a badly formatted table reproduction. Treat it as LOW CONFIDENCE.
- Birmingham 2008/09 (£27.1m) is derived from a stated £22m (44.8%) fall. The same table reproductions give Birmingham £56m for both 2009/10 and 2010/11, which may be a reproduction error.
- Southampton 2011/12: matchday only (£11.8m).

**Lower leagues (thin, as expected).** Splits exist only for recent promotions, mostly from free Swiss Ramble Substack previews:
- League One to Championship, both seasons split: Barnsley 2019, Plymouth 2023, Ipswich 2023, Derby 2024, Portsmouth 2024.
- Coventry 2020: Championship side only.
- Sunderland 2022: Championship side only.
- Luton 2019: none for the League One side.
- League Two to League One: Wrexham 2024, which is atypical (commercial £18.7m).
- Older League One totals with no split: Norwich 2009/10, Southampton 2009/10, Leicester 2008/09, Huddersfield 2011/12, Bournemouth 2011/12, Wolves 2013/14 (with parachute).
- No League Two club data apart from Wrexham.

## Coverage of division_revenue.csv (67 rows)
**Premier League:** a total for every season 2008/09–2024/25 except the exact 2009/10 figure (only "exceeded £2bn"; broadcasting £1,040m and commercial £459m are stated). A full split exists for 2012/13–2019/20 and 2021/22–2024/25.

**Championship:** totals for 2008/09, 2010/11, 2011/12, 2013/14–2024/25. 2009/10 is only ">£400m", about £406m implied. 2012/13 is derived (about £437m).
- Splits: 2017/18 (percentages only, so derived), 2020/21 (matchday only), 2022/23 (matchday and commercial; broadcasting derived), 2023/24 (matchday and commercial; broadcasting derived), 2024/25 (full).

**League One and League Two:**
- Totals: 2013/14–2018/19, 2020/21, 2021/22.
- Averages only: 2011/12, 2022/23, 2023/24.
- 2012/13 League One is derived.
- 2019/20: only the combined League One plus League Two figure (about £264m, derived).
- Nothing for 2008/09–2010/11, or for 2024/25 (the ARFF 2026 web page gives League One and League Two losses only).

**Restatements:** Deloitte restates prior years between editions, for example Championship 2013/14 at £491m vs £490m, League One 2013/14 at £148m vs £145m, and PL 2016/17 at £4,552m vs £4,556m. Both versions are kept and labelled by edition.

## Doubts and caveats
- WebFetch summarises pages through a small model. Chart values pulled from PDFs (ARFF 2016–2019 and 2021 PL splits) were checked by making sure the three streams add up to the total. ARFF 2016 printed the streams in a different order, and I corrected the mapping for 2012/13 using the known 2013/14 split.
- COVID seasons are distorted: 2019/20 accounts often ran 13 months to July 2020 (Norwich, WBA, Burnley, Sheffield Utd) or pushed revenue into 2020/21, and 2020/21 has almost no matchday income. Do not use these seasons as baselines for a model.
- Year ends differ: 31 May (Wolves, Brighton, Cardiff, Villa, older Norwich), 30 June (most clubs), 31 July (Bournemouth 2015/16, Swansea 2016/17), August (Birmingham). Leicester and Norwich changed theirs.
- Swiss Ramble's 2010/11 and 2011/12 figures for Wolves were relabelled from the article's year-end labels ("2010" = 2009/10). Check before relying on them.
- Companies House: the company search and the filing-history pages were readable through WebFetch (Watford, company 00104194; accounts made up to 30 June each year; PDF links listed). The document PDF itself (the 2016 accounts) would not download (client error), so no figures came from Companies House.
- Web search budget ran out at the end of the session (200 searches). Fetching already-known URLs still worked.

## Documents that would fill the gaps if uploaded
1. **Deloitte ARFF full reports or databooks** (not the highlights). The highlights lack Championship splits and League One / League Two detail:
   - ARFF 2010, 2011, 2012: League One / League Two totals for 2008/09–2010/11, and the exact PL and Championship figures for 2009/10.
   - ARFF 2014: Championship, League One and League Two for 2012/13.
   - ARFF 2021: Championship, League One and League Two for 2019/20. The PDF fetched cut off before the Football League section.
   - ARFF 2022, 2023, 2024: Championship matchday / broadcast / commercial for 2020/21–2022/23.
   - ARFF 2026 full report: League One and League Two revenue for 2024/25.
   - Any edition's "Football League clubs' revenue by stream" chart would give the Championship split by season.
2. **Club statutory accounts (Companies House PDFs)**, turnover note:
   - Reading FC 2011/12 and 2012/13.
   - Watford 2014/15 and 2015/16.
   - Hull City 2015/16.
   - Middlesbrough 2015/16 (split).
   - Swansea 2010/11 and 2011/12.
   - Norwich 2010/11, 2011/12 and 2020/21.
   - Blackpool 2009/10 and 2010/11.
   - Burnley 2008/09 and 2009/10.
   - Birmingham 2008/09 and 2009/10.
   - Wolves 2008/09 and 2009/10.
   - Newcastle 2009/10, 2016/17 and 2017/18.
   - Brighton 2016/17 and 2017/18.
   - Huddersfield 2016/17 and 2017/18.
   - Cardiff 2017/18 and 2018/19.
   - Sheffield United 2018/19 and 2019/20.
   - Luton 2018/19 (League One).
   - Coventry 2019/20 (League One).
   - Sunderland 2021/22 (League One).
3. **Swiss Ramble paid Substack posts**, or full Twitter threads, for the 2016–2019 promotion clubs (Brighton, Huddersfield, Newcastle, Cardiff, Sheffield Utd, Hull, Middlesbrough). They usually give matchday / broadcasting / commercial for both the current and prior year.
4. **Kieran Maguire / Price of Football club databases** (paid), which cover the lower leagues by revenue stream.
