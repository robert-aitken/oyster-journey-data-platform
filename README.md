# Oyster Journey Data Platform

## Project overview

This repository is a local-first data project for loading Oyster-style journey history into DuckDB and transforming it with dbt.

The public repo now supports two workflows:

- a public synthetic sample workflow for validation and demonstration
- a private local workflow for loading real Oyster exports on your own machine

The project includes a config-based DuckDB ingestion script, a static synthetic sample writer, a dbt DuckDB project, package configuration, and a small Python requirements file.

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

## Public sample workflow

The public sample workflow uses:

- `config/oyster_project.sample.yml`
- synthetic CSV files under `data/sample/oyster_journey/`
- `python/generation/scripts/write_synthetic_oyster_journey_sample.py`
- `python/ingestion/scripts/load_raw_oyster_journey_history_duckdb.py`

Typical setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Regenerate the sample files if needed:

```bash
python3 python/generation/scripts/write_synthetic_oyster_journey_sample.py
```

Load the sample data into DuckDB:

```bash
python3 python/ingestion/scripts/load_raw_oyster_journey_history_duckdb.py
```

Then run dbt:

```bash
cd dbt/oyster_dbt
dbt deps
dbt compile --profiles-dir profiles
dbt run --select tag:OYSTER_JOURNEY --profiles-dir profiles
dbt test --select tag:OYSTER_JOURNEY --profiles-dir profiles
dbt ls --select tag:OYSTER_JOURNEY --profiles-dir profiles
```

dbt expects a local profile file at `dbt/oyster_dbt/profiles/profiles.yml`, created from `dbt/oyster_dbt/profiles.template.yml`. The local profile file should not be committed.

## Private local workflow

Real Oyster exports can be loaded locally by creating:

- `config/oyster_project.local.yml`

That local config can point to private paths such as:

- `data/import/oyster_journey`

Then run:

```bash
python3 python/ingestion/scripts/load_raw_oyster_journey_history_duckdb.py --config-path config/oyster_project.local.yml
```

This keeps the public sample workflow and the private local workflow on the same DuckDB/dbt structure while keeping private inputs out of version control.

## Repository structure

- `.gitignore`: ignores local environment files, database files, dbt artefacts, and local profiles
- `requirements.txt`: minimal Python dependencies for DuckDB ingestion and local dbt work
- `config/oyster_project.sample.yml`: committed sample config for the public workflow
- `python/generation/scripts/write_synthetic_oyster_journey_sample.py`: rewrites the synthetic sample CSV files
- `python/ingestion/scripts/load_raw_oyster_journey_history_duckdb.py`: loads configured CSV inputs into the DuckDB raw table
- `data/sample/oyster_journey/`: synthetic public sample CSV files
- `dbt/oyster_dbt/`: dbt project containing sources, staging models, intermediate models, marts, macros, and dbt package configuration

## Data privacy

- Real Oyster journey CSV exports are not included in the repository.
- DuckDB database files are not included in the repository.
- Local `dbt/oyster_dbt/profiles/profiles.yml` is not included in the repository.
- `config/oyster_project.local.yml` is not included in the repository.
- The public sample data uses the fake identifier `999999999`.
- Synthetic sample rows are fake and are not derived from private journeys.

## dbt models

Current dbt outputs include:

- `oyster.staging.stg_oyster_journey_history`
- `oyster.intermediate.int_oyster_journey_events`
- `oyster.intermediate.int_oyster_daily_spend`
- `oyster.mart.mart_oyster_journey_summary`
- `oyster.mart.mart_oyster_daily_spend`

## Current status / next steps

The current public repository represents a working sample-to-dbt workflow, plus a local private-data path for loading real Oyster exports on the same structure.

Next steps are likely to include:

- broadening model coverage
- adding more data tests and lightweight documentation
- refining the public sample workflow and analysis outputs
