# Alternative histories of English football

"What if" versions of English football from 2008/09 onwards, simulated through the
league pyramid (Premier League to National League) with one shared engine. The
full project spec lives in the project instructions; this repo holds the engine,
the validated data and the scenario outputs.

## Status

| Stage | What | Status |
|---|---|---|
| E1 | Every league result 2008/09–2025/26 loaded; real final tables reproduced | Built, awaiting verification against official tables |
| E2 | Ratings model and back-test | Built, awaiting Mus's check ([docs/e2_validation.md](docs/e2_validation.md)) |
| E3 | Season simulator | Built, awaiting Mus's check ([docs/e3_validation.md](docs/e3_validation.md)) |
| E4 | Finance model | Built, awaiting Mus's check ([docs/e4_validation.md](docs/e4_validation.md)) |

Scenarios are listed in [docs/scenario_register.md](docs/scenario_register.md).
Judgement calls are logged in [docs/assumptions_log.md](docs/assumptions_log.md).

## Rebuilding the data

```
pip install -r requirements.txt
python -m altpl.sources.fetch   # download pinned GitHub sources, write data/sources/*.csv
python -m altpl.build_e1        # results, tables, membership, validation report
python -m altpl.build_e2        # ratings, back-tests, docs/e2_validation.md (~20 min, 4 cores)
python -m altpl.build_e3        # simulator tests, docs/e3_validation.md (~20 min)
python -m altpl.build_e4        # finance price list and tests, docs/e4_validation.md (~30 min)
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
  ratings.py           E2 Dixon-Coles ratings on one scale across divisions, odds-implied goals
  backtest.py          E2 back-tests and a light season Monte Carlo
  build_e2.py          stage E2 pipeline; e2_report.py writes the validation report
  simulator.py         E3 Monte Carlo of the whole pyramid, season by season (World = a scenario's rules)
  outputs.py           standard output tables: expected tables, who's where, champions, variants
  build_e3.py          stage E3 re-simulation tests and validation report
  finance_data.py      E4 price list: sourced payments turned into one value per season and item
  finance.py           E4 finance model: revenue difference from reality per club, season and run
  build_e4.py          stage E4 checks against sources and validation report
data/
  sources/             standardised copy of each source (committed)
  reference/           hand-maintained facts: clubs, adjustments, league rules, exceptions
  reference/finance/sources/  sourced finance figures, every row with its URL
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
- `data/processed/ratings.csv`: attack, defence and strength (with standard errors) for every club-season, all divisions on one scale.
- `data/processed/division_levels.csv`: average strength of each division-season and the gap to the division above.
- `data/processed/ratings_params.json`: fitted home advantage, rho and the tuned settings.
- `data/processed/e2_backtest.xlsx` and `docs/e2_validation.md`: every back-test table.
- `data/processed/e3_backtest.xlsx` and `docs/e3_validation.md`: simulator tests (reality reproduced, single-season re-simulations, knock-on runs).
- `data/processed/e3_knock_on_example.xlsx`: the standard output workbook, for reality fully simulated 2008/09-2025/26.
- `data/processed/finance_prices.csv`: the E4 price list, one value per season and item with its status (sourced, derived, estimate, filled) and source.
- `data/processed/e4_backtest.xlsx` and `docs/e4_validation.md`: finance checks against sources and real promotion seasons.
- `data/processed/e4_finance_example.xlsx`: standard outputs plus finance sheets, for the example run.

## Running a scenario

```python
from altpl import simulator as S, outputs as O, finance as F
R = S.Reality()
w = S.real_world(R, start=2009, end=2025)   # reality's rules from 2009/10
w.removed = {"manchester_city": 2009}       # scenario change: club gone from 2009/10
w.name = "S01 1A"
sim = S.simulate(w, runs=10_000, reality=R)  # real results kept where they happened
fr = F.finance(sim, R)                       # revenue difference from reality (E4)
O.write_workbook(sim, R, "s01_1a.xlsx", extra=F.write_sheets(fr))
```

`w.sizes[(season, tier)]` sets division sizes, `w.rules` the promotion, play-off and
relegation places, `anchored=False` simulates every fixture, and `w.step_up` /
`w.money_boost` are the optional sensitivities (off by default).
