# UEFA places and payments: gaps and doubts

All figures come from pages fetched in this session with WebFetch (curl to these sites is blocked by the proxy). WebFetch returns a small-model summary, not the raw page, so read the figures as transcriptions.

## euro_places.csv / cup_places.csv (source: Wikipedia "20XX–YY Premier League" articles)
- WebFetch flattens rowspans in the league table. It shows a qualification note only on the first row of a spanned block, so "1-3 group stage" style ranges come from the block structure plus the footnotes. One fetch said 2009–10 had no rowspans at all, which cannot be checked from markdown. For 2009–10 the 6th-place (Aston Villa) stage of "EL play-off round" is inferred: the footnote says the League Cup winners' spot passed to 6th, and the League Cup berth that season was the EL play-off (the 2010–11 footnote says the League Cup was "worth a third qualification round spot"). Treat this one as uncertain.
- 2008–09: the footnote says 6th got the EL play-off and 7th got the EL 3QR. Which cup each berth came from (FA Cup or League Cup) is not split out exactly.
- 2011–12: Chelsea's FA Cup EL spot was forfeited. Per the page it was NOT passed down; instead 4th-placed Spurs dropped to the EL group stage.
- 2016–17: Man Utd's passed-down EL group-stage spot was vacated without replacement once they won the UEL.
- 2024–25: Forest first held the League Cup UECL play-off berth, then swapped with Crystal Palace (multi-club ownership).
- 2025–26: taken from the Wikipedia article as it stood in Oct 2026 (season complete: Arsenal champions, EPS 5th place, Man City won both cups, Crystal Palace won the UECL). No second source was used.
- Fair Play places found: 2010–11 (Fulham, 8th, EL 1QR) and 2014–15 (West Ham, 12th, EL 1QR). No other season's table footnotes mention Fair Play. I did not check the Fair Play rules separately.
- I did not fetch "English football clubs in international competitions" or "20XX-YY in English football". All allocation data comes from the PL season articles.

## uefa_payments.csv
- Sources: UEFA per-club distribution PDFs (2009/10-2018/19), UEFA Financial Reports (2019/20, 2020/21, 2022/23, 2024/25), and press figures citing UEFA (AP/EFE/TNT) for 2021/22 and 2023/24 (rounded, partial).
- Amounts are in EUR. 2019/20 onward values were printed in EUR000 and have been multiplied by 1000. 2019/20 and 2020/21 are NET of the COVID-19/ECA deduction.
- Where a PDF had no total column (2009/10 CL and UEL, 2010/11 CL except via news, 2010/11 UEL), I summed the listed components; see the notes column.
- 2009/10 UEL: the table has columns only up to the semi-final bonus, so Fulham's final payment is missing (the total is a lower bound).
- 2013/14 CL: Man City's amount was withheld for FFP non-compliance (footnote). Arsenal's play-off payment is not in that document.
- Early tables cover the final phase only. Clubs knocked out in qualifying or play-offs (e.g. Aston Villa 2009/10 and 2010/11, Hull 2014/15, Southampton and West Ham 2015/16, West Ham 2016/17, Burnley 2018/19) have no figure. Any solidarity or qualifying-round payments are excluded.
- The per-column mapping is sometimes uncertain (garbled PDF headers), but totals are as printed or as summed. "stage_reached" is mostly inferred from which knockout bonus columns were paid.
- Super Cup: included only where seen (2019 Liverpool/Chelsea from the 2019/20 report, 2023 Man City EUR4.5m from AP). Super Cups in other years were not collected.

### GAPS
- 2020/21 UEL (Man Utd, Arsenal, Spurs, Leicester): the per-club table could not be extracted from the 2020/21 financial report (EN and FR text truncated; the annex has totals only).
- 2021/22: the UEFA report PDF errored on fetch. Only rounded press totals exist for Liverpool (~120m), Man City (108.7m) and Chelsea (91.9m). Missing: Man Utd UCL, West Ham and Leicester UEL, Leicester and Spurs UECL.
- 2023/24: the UEFA report PDF errored on fetch. Only rounded press figures exist for Man City (110.4m + 4.5m USC), Arsenal (94m), Man Utd (60.7m) and Newcastle (34.4m). Liverpool UEL appears only as "less than 27m". Missing: West Ham and Brighton UEL, Aston Villa UECL.
- 2025/26: not yet published by UEFA (the financial report is due ~Jan 2027).
- Possible retry routes: the 2021/22 and 2023/24 UEFA financial report PDFs (URLs in the session: editorial.uefa.com .../uefa_financial_report_2021-22_en.pdf and .../uefa_financial_report_23-24_.pdf) failed via WebFetch, perhaps because of size. Swiss Ramble (paywalled) says all its seasons come from UEFA financial reports.
- Rejected source: theesk.org compilation (GBP, partly estimated, contains apparent errors).
