# Local Airflow dbt Dependencies

## Purpose

This note explains how dbt was added to the local Airflow runtime for the Oyster project, why `git` was also needed, and how the setup was tested from inside the Airflow container.

The key point is:

```text
dbt runs inside the Airflow container, not inside the local Python environment.
```

So dbt-related dependencies need to be available inside the Airflow runtime.

## Add dbt To The Airflow Python Environment

Python packages for the local Astro Airflow environment are added to:

```text
orchestration/airflow/requirements.txt
```

For the Oyster project, dbt support was added using:

```text
dbt-duckdb
```

`dbt-duckdb` provides the DuckDB adapter for dbt and installs dbt Core as part of its dependency chain.

The Oyster project also needs other Python packages used by the ingestion workflow:

```text
duckdb
PyYAML
```

A typical local Airflow requirements file for this checkpoint includes:

```text
duckdb
dbt-duckdb
PyYAML
```

## Add Git To The Airflow Docker Image

dbt also expects the `git` command to be available.

This is not a Python package, so it does not belong in `requirements.txt`.

`git` is an operating system command inside the Airflow container, so it is added through the Airflow Dockerfile:

```text
orchestration/airflow/Dockerfile
```

Before the change, the Dockerfile only contained:

```dockerfile
FROM astrocrpublic.azurecr.io/runtime:3.2-5
```

The Dockerfile was changed to:

```dockerfile
FROM astrocrpublic.azurecr.io/runtime:3.2-5

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER astro
```

## What The Dockerfile Change Does

```dockerfile
FROM astrocrpublic.azurecr.io/runtime:3.2-5
```

Uses the Astronomer Airflow runtime image as the base image.

```dockerfile
USER root
```

Temporarily switches to the Linux `root` user so that operating system packages can be installed.

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
```

Installs `git` inside the Airflow image.

The cleanup commands remove cached package files and package lists to keep the image smaller.

```dockerfile
USER astro
```

Switches back to the normal `astro` user expected by the Airflow runtime.

This is important because `root` is only needed for the package installation step.

## Python Packages Versus Operating System Tools

Use `requirements.txt` for Python packages:

```text
duckdb
dbt-duckdb
PyYAML
```

Use the Dockerfile for operating system tools:

```text
git
```

The distinction is:

```text
Python packages -> orchestration/airflow/requirements.txt
Operating system tools -> orchestration/airflow/Dockerfile
```

## Why dbt Needed Git

When `dbt debug` was first run inside the Airflow container, dbt reported:

```text
Required dependencies:
 - git [ERROR]

Error from git --help: Could not find command, ensure it is in the user's PATH: "git"
```

This meant dbt was installed, but the Airflow container did not have the `git` command available.

dbt checks for `git` because dbt projects often use packages and dependencies that may come from Git repositories or require Git-related functionality.

After adding `git` to the Dockerfile and rebuilding the image, the check passed.

## Rebuild Local Airflow

After updating `requirements.txt` and the Dockerfile, rebuild the local Airflow image from the Astro project folder:

```bash
cd orchestration/airflow
astro dev stop
astro dev start
```

The expected output includes:

```text
Project image has been updated
Project started
Airflow UI: http://airflow.localhost:6563
```

## Open A Shell Inside The Airflow Container

After Airflow starts, open a shell inside the Airflow container:

```bash
astro dev bash -a
```

The prompt should change from the local machine prompt to an Airflow container prompt similar to:

```text
astro@<container_id>:/usr/local/airflow$
```

This matters because the checks must run inside the Airflow container.

## Check Git Inside Airflow

From inside the Airflow container:

```bash
which git
git --version
```

Observed output:

```text
/usr/bin/git
git version 2.47.3
```

This confirms that `git` is now installed inside the Airflow container.

## Run dbt Debug Inside Airflow

Change into the dbt project folder inside the mounted Oyster project:

```bash
cd /usr/local/airflow/oyster_project/dbt/oyster_dbt
```

Then run:

```bash
dbt debug --profiles-dir profiles
```

This command is run from inside the dbt project folder so that the relative DuckDB path in the dbt profile resolves correctly.

The successful output included:

```text
profiles.yml file [OK found and valid]
dbt_project.yml file [OK found and valid]
Required dependencies:
 - git [OK found]
Connection test: [OK connection ok]
All checks passed!
```

This confirms that dbt can:

```text
find the dbt project
find profiles.yml
find git
load the dbt-duckdb adapter
connect to the DuckDB database
```

## Why The Working Directory Matters

The dbt profile used this DuckDB path:

```text
../../database/duckdb/oyster.duckdb
```

This path is relative.

When dbt was run from the wrong folder, the DuckDB path resolved incorrectly.

When dbt was run from:

```text
/usr/local/airflow/oyster_project/dbt/oyster_dbt
```

the relative path resolved correctly back to the Oyster DuckDB database.

This is why the dbt commands should either:

```text
run from the dbt project folder
```

or use paths that are safe from the chosen working directory.

## List dbt Models From Inside Airflow

After `dbt debug` passed, dbt was checked further with:

```bash
dbt ls --profiles-dir profiles
```

Observed output included:

```text
Found 5 models, 5 data tests, 1 source, 632 macros
```

The listed resources included:

```text
oyster_dbt.intermediate.int_oyster_daily_spend
oyster_dbt.intermediate.int_oyster_journey_events
oyster_dbt.marts.mart_oyster_daily_spend
oyster_dbt.marts.mart_oyster_journey_summary
oyster_dbt.staging.oyster.stg_oyster_journey_history
source:oyster_dbt.raw.oyster_journey_history
```

This confirmed that dbt could parse the Oyster dbt project from inside Airflow.

## Run dbt Build From Inside Airflow

The Oyster dbt models and tests were then built from inside the Airflow container:

```bash
dbt build --profiles-dir profiles --select tag:OYSTER_JOURNEY
```

Observed result:

```text
Finished running 5 table models, 5 data tests
Completed successfully
Done. PASS=10 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=10
```

This confirmed that the Airflow container can run the Oyster dbt build successfully.

## Result

The local Airflow runtime now has the dbt support needed for the Oyster project.

Confirmed inside the Airflow container:

| Check | Result |
|---|---|
| `git` command available | Passed |
| dbt installed | Passed |
| dbt-duckdb adapter available | Passed |
| `profiles.yml` found | Passed |
| `dbt_project.yml` found | Passed |
| DuckDB connection test | Passed |
| `dbt ls` | Passed |
| `dbt build --select tag:OYSTER_JOURNEY` | Passed |

This means the dbt part of the Oyster workflow is ready to be called by an Airflow DAG.
