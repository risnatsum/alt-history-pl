# EUR→GBP exchange rate (GBP per 1 EUR), 2008–2026

**Series:** ECB euro foreign exchange reference rate, EUR 1 = x GBP (the official ECB series EXR.*.GBP.EUR.SP00.A).
**Where the numbers come from:** Deutsche Bundesbank "Exchange rate statistics" / "Wechselkursstatistik" PDFs, table "Annual and monthly averages". The Bundesbank reproduces the ECB reference rates. I could not read the ECB Data Portal and ECB API directly: robots.txt blocks the API and the portal page is rendered by JavaScript. Each CSV row carries the URL of the PDF it was read from.

## Coverage
- Annual 2008–2025: official annual averages (mean of daily rates). 2008–2011 come from the Jan-2012 issue; 2012–2025 come from the current table wk1e1213 (dated 15.09.2026).
- Monthly 2008-01 to 2026-09: complete, no gaps. They come from 9 PDF issues; the source_url column says which issue each value came from.
- 2026: **DERIVED** year-to-date value of 0.86352, the unweighted mean of the Jan–Sep 2026 monthly averages. It is not an official figure.

## Checks
- For every year, the mean of the 12 monthly averages matches the official annual figure within 0.0006. The small gap comes from weighting by trading days.
- Overlapping months in different Bundesbank issues give identical values.
- Spot checks against the inverse of ONS THAP / BoE XUMAERS (EUR per GBP, monthly) agree. Examples: Jan 2008 1/1.3383 = 0.7472 vs 0.74725; Oct 2016 1/1.1190 = 0.8937 vs 0.89390. Source: https://cy.ons.gov.uk/economy/nationalaccounts/balanceofpayments/timeseries/thap/diop
- 2024 annual 0.84662 matches the Bank of Finland figure exactly.
- **2025 discrepancy:** the Bundesbank gives 0.85679 in both wk1e1213 and wk1e1011 (dated 30-09-2026). The Bank of Finland "average annual exchange rates 2025" page gives 0.85687 (USD 1.1300 matches; JPY also differs slightly, 169.04 vs 169.07). I used the Bundesbank value. The difference is 0.01%.

## July–June season averages
These are unweighted means of the 12 monthly averages, Jul Y to Jun Y+1. Like the 2026 YTD, they are derived from the monthly CSV rows.
2008/09 0.85586 · 2009/10 0.87910 · 2010/11 0.85725 · 2011/12 0.84499 · 2012/13 0.82543 · 2013/14 0.83435 · 2014/15 0.76192 · 2015/16 0.74906 · 2016/17 0.85968 · 2017/18 0.88598 · 2018/19 0.88167 · 2019/20 0.87768 · 2020/21 0.88628 · 2021/22 0.84687 · 2022/23 0.86982 · 2023/24 0.85887 · 2024/25 0.84048 · 2025/26 0.86909

The script that builds the CSV from the transcribed values is build.py in this folder.
