# Local Airflow Dependencies

## Purpose

This note explains how to add Python and dbt dependencies to the local Airflow environment used by the Oyster project.

The key point is:

```text
Packages installed in your local Python environment are not automatically available inside Airflow.
```

The Oyster project may run successfully in a local Python virtual environment or in VS Code, but local Airflow runs inside Docker containers created by Astro. Those containers have their own Python environment.

If an Airflow DAG imports a package, or calls a script that imports a package, that package must be installed inside the Airflow container.

## Environment Note

The commands in this note were tested from a local macOS setup.

The principle is operating-system agnostic:

```text
local Python environment
does not equal
Airflow container Python environment
```

The same idea applies on macOS, Windows, Linux, or GitHub Codespaces if Airflow is running inside a container.

## How To Add Dependencies To Local Airflow

Add Python dependencies to the Astro Airflow requirements file:

```text
orchestration/airflow/requirements.txt
```

For the Oyster project, the following dependencies were needed:

```text
duckdb
dbt-duckdb
PyYAML
```

`dbt-duckdb` provides the DuckDB adapter for dbt and installs dbt Core as part of its dependency chain.

`PyYAML` is used for YAML configuration files.

After updating `requirements.txt`, rebuild or restart the local Astro Airflow environment from the Astro project folder:

```bash
cd orchestration/airflow
astro dev start
```

If the environment is already running, restart it:

```bash
astro dev restart
```

Then open a shell inside the Airflow container:

```bash
astro dev bash -a
```

Run checks inside the container:

```bash
python -c "import duckdb; print('duckdb OK:', duckdb.__version__)"
python -c "import yaml; print('pyyaml OK')"
dbt --version
python -c "import dbt.adapters.duckdb; print('dbt-duckdb OK')"
```

Expected result:

```text
duckdb OK: <version>
pyyaml OK
dbt Core version is shown
dbt-duckdb OK
```

Exit the container:

```bash
exit
```

## Why This Is Needed

The local development environment and the Airflow Docker container are separate environments.

```text
Local development environment
├── editor or terminal
├── optional local .venv
├── local Python packages
└── local command-line tools

Airflow container environment
├── Airflow
├── container Python
├── packages from orchestration/airflow/requirements.txt
└── commands available inside the container
```

A package can be installed locally but still be missing inside Airflow.

For example:

```text
duckdb works locally
does not mean
duckdb works inside the Airflow container
```

That is why dependency checks need to be run from inside the Airflow container.

## What Had Already Been Confirmed

The local Astro Airflow project could start successfully:

```bash
astro dev start
```

Observed output:

```text
Project image has been updated
Project started
Airflow UI: http://airflow.localhost:6563
```

The wider Oyster repository was mounted into the Airflow containers at:

```text
/usr/local/airflow/oyster_project
```

The mount check confirmed that key Oyster project files were visible inside the container:

```bash
test -f /usr/local/airflow/oyster_project/config/oyster_project.local.yml && echo "config found"
test -f /usr/local/airflow/oyster_project/python/ingestion/scripts/load_raw_oyster_journey_history_duckdb.py && echo "ingestion script found"
test -d /usr/local/airflow/oyster_project/dbt/oyster_dbt && echo "dbt project found"
```

Observed output:

```text
config found
ingestion script found
dbt project found
```

This proved that Airflow could see the mounted Oyster files.

It did not prove that Airflow had the required Python and dbt dependencies installed.

## Temporary Missing Dependency Test

A temporary local test DAG was created to show what happens when a DAG imports a package that is missing inside the Airflow container.

The temporary DAG file was:

```text
orchestration/airflow/dags/test_missing_duckdb_dependency.py
```

The test DAG used this code:

```python
from airflow.decorators import dag, task
from pendulum import datetime
import duckdb

@dag(
    dag_id="test_missing_duckdb_dependency",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["test", "dependency-check"],
)
def test_missing_duckdb_dependency():
    @task
    def check_duckdb_import():
        print(f"duckdb is available: {duckdb.__version__}")

    check_duckdb_import()


test_missing_duckdb_dependency()
```

This test deliberately imported `duckdb`.

At this point, `duckdb` had not been added to the Airflow container environment.

The Airflow UI and logs showed an error similar to:

```text
ModuleNotFoundError: No module named 'duckdb'
```

This confirmed that the dependency was missing from the Airflow container.

Because `import duckdb` was placed at the top of the DAG file, Airflow tried to import `duckdb` while loading the DAG file. If a package imported by a DAG file is missing, Airflow can fail before the task logic runs properly.

The lesson is:

```text
If a DAG file imports a package directly, that package must be installed in the Airflow container before Airflow can load the DAG cleanly.
```

This is also relevant if the DAG calls another Python script. If that script imports `duckdb`, then the task can fail at runtime unless `duckdb` is installed in the Airflow container.

The temporary DAG was only used for testing and should not be kept in the project:

```bash
rm -f orchestration/airflow/dags/test_missing_duckdb_dependency.py
```

## Initial Dependency Check

A shell was opened inside the running Airflow `api-server` container:

```bash
cd orchestration/airflow
astro dev bash -a
```

The following dependency checks were run inside the container:

```bash
python -c "import duckdb; print('duckdb OK:', duckdb.__version__)"
python -c "import yaml; print('pyyaml OK')"
dbt --version
python -c "import dbt.adapters.duckdb; print('dbt-duckdb OK')"
```

The initial result was:

```text
duckdb: missing
pyyaml: available
dbt: missing
dbt-duckdb: missing
```

The errors included:

```text
ModuleNotFoundError: No module named 'duckdb'
bash: dbt: command not found
ModuleNotFoundError: No module named 'dbt'
```

## Requirements File Update

The missing dependencies were added to:

```text
orchestration/airflow/requirements.txt
```

Dependencies added:

```text
duckdb
dbt-duckdb
PyYAML
```

`PyYAML` was already available in the container, but it was added explicitly because the Oyster project uses YAML configuration.

Adding it explicitly makes the Airflow environment easier to understand and avoids relying on a package being present by accident.

## Rebuild And Restart Airflow

After updating `requirements.txt`, the local Airflow image was rebuilt and restarted:

```bash
astro dev start
```

Observed output:

```text
Project image has been updated
Project started
Airflow UI: http://airflow.localhost:6563
```

## Final Dependency Check

A shell was opened inside the Airflow container again:

```bash
astro dev bash -a
```

The dependency checks were rerun inside the container:

```bash
python -c "import duckdb; print('duckdb OK:', duckdb.__version__)"
python -c "import yaml; print('pyyaml OK')"
dbt --version
python -c "import dbt.adapters.duckdb; print('dbt-duckdb OK')"
```

Observed output:

```text
duckdb OK: 1.5.4
pyyaml OK
Core:
  - installed: 1.11.11
  - latest:    1.11.11 - Up to date!

Plugins:
  - duckdb: 1.10.1 - Up to date!

dbt-duckdb OK
```

## Result

The Airflow container now has:

| Dependency | Result |
|---|---|
| DuckDB | Available |
| PyYAML | Available |
| dbt Core | Available |
| dbt-duckdb | Available |

This means the Airflow container has the Python and dbt dependencies needed for future Oyster DAG tasks that depend on DuckDB, YAML configuration and dbt.
