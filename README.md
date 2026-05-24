# Oyster Journey Data Platform

## Project overview

This repository is a local-first data project for working with private Oyster journey history exports.

It combines a Python ingestion step that loads CSV data into DuckDB with a dbt project that transforms the raw table into analysis-ready models. The public repository includes the project `.gitignore`, the DuckDB ingestion script, the dbt project structure, dbt models, dbt macros, and dbt package configuration through `packages.yml` and `package-lock.yml`.

## Current pipeline

`CSV files -> Python ingestion -> DuckDB raw table -> dbt staging -> dbt intermediate -> dbt marts`

dbt flow:

`raw -> staging -> intermediate -> marts`

Current key tables and models:

- `oyster.raw.oyster_journey_history`
- `oyster.staging.stg_oyster_journey_history`
- `oyster.intermediate.int_oyster_journey_events`
- `oyster.intermediate.int_oyster_daily_spend`
- `oyster.mart.mart_oyster_journey_summary`
- `oyster.mart.mart_oyster_daily_spend`

## Repository structure

- `.gitignore`: ignores local environment files, database files, dbt artefacts, and local profiles
- `python/ingestion/scripts/load_raw_oyster_journey_history_duckdb.py`: loads private Oyster CSV exports into the DuckDB raw table
- `dbt/oyster_dbt/`: dbt project containing source definitions, staging models, intermediate models, marts, macros, and package configuration

## Data privacy

- Real Oyster journey CSV exports are not included in the repository.
- DuckDB database files are not included in the repository.
- Local `profiles.yml` is not included in the repository.
- The project is designed to run against local private CSV exports.

## How to run locally

1. Create a local Python environment and install the dependencies needed for DuckDB ingestion and dbt.
2. Place private Oyster CSV exports in `data/import/oyster_journey/`.
3. Run the DuckDB ingestion script to load the raw data into `oyster.raw.oyster_journey_history`.
4. Run dbt locally from `dbt/oyster_dbt` using a local `profiles/profiles.yml` file based on `profiles.template.yml`.

## dbt commands

```bash
cd dbt/oyster_dbt
dbt compile --profiles-dir profiles
dbt run --select tag:OYSTER_JOURNEY --profiles-dir profiles
dbt test --select tag:OYSTER_JOURNEY --profiles-dir profiles
```

## Current status / next steps

The current repository represents a working local analysis pipeline from private Oyster CSV exports through to dbt marts in DuckDB.

Next steps are likely to include:

- broadening model coverage
- adding more tests and lightweight documentation
- refining local analysis outputs
