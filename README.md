# Alternative histories of English football

"What if" versions of English football from 2008/09 onwards, simulated through the
league pyramid (Premier League to National League) with one shared engine. The
full project spec lives in the project instructions; this repo holds the engine,
the validated data and the scenario outputs.

## Status

| Stage | What | Status |
|---|---|---|
| E1 | Every league result 2008/09–2025/26 loaded; real final tables reproduced | Built, awaiting verification against official tables |
| E2 | Ratings model and back-test | Not started |
| E3 | Season simulator | Not started |
| E4 | Finance model | Not started |

Scenarios are listed in [docs/scenario_register.md](docs/scenario_register.md).
Judgement calls are logged in [docs/assumptions_log.md](docs/assumptions_log.md).

## Rebuilding the data

```
pip install -r requirements.txt
python -m altpl.sources.fetch   # download pinned GitHub sources, write data/sources/*.csv
python -m altpl.build_e1        # results, tables, membership, validation report
python -m pytest
```

`fetch` needs only GitHub. football-data.co.uk is not reachable from the build
environment, so its season CSVs (downloaded by hand) are committed under
`data/sources/footballdata_csv/`.

## Layout

```
altpl/
  config.py            seasons, divisions, pinned source versions
  clubs.py             one club_id per club across every source spelling
  sources/             openfootball parser, download + standardise sources
  results.py           reconcile sources into one result per fixture
  tables.py            league tables with deductions and points-per-game
  build_e1.py          stage E1 pipeline and validation report
data/
  sources/             standardised copy of each source (committed)
  reference/           hand-maintained facts: clubs, adjustments, league rules, exceptions
  processed/           pipeline outputs (results, tables, membership, real_tables.xlsx)
docs/                  assumptions log, scenario register, validation report
tests/
```

## Key outputs

- `data/processed/results.csv`: one row per league match, with how many sources agree.
- `data/processed/tables.csv`: real final tables with raw points, deductions, PPG and each club's real outcome.
- `data/processed/membership.csv`: which division every club was in each season, 2008/09–2026/27.
- `data/processed/real_tables.xlsx`: the same tables, one sheet per division.
- `docs/e1_validation.md`: match counts, source disagreements, consistency checks, champions.
