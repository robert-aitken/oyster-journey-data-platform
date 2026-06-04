# Local Airflow Volume Mount

## Official Documentation

Astronomer documents that a `docker-compose.override.yml` file can be added at the top level of an Astro project to override local Docker Compose configuration, including mounted volumes.

Official reference:

- [Example: Mounting A Volume With Additional Files](https://www.astronomer.io/docs/astro/cli/run-airflow-locally#example-mounting-a-volume-with-additional-files)

## Official Volume Mount Pattern

Astronomer's example mounts one local folder into one Airflow service.

```yaml
services:
  scheduler:
    volumes:
      - /home/astronomer_project/custom_dependencies:/usr/local/airflow/custom_dependencies:ro
```

The important pattern is:

```text
services:
  <airflow-service-name>:
    volumes:
      - <host-path>:<container-path>:<optional-read-only-flag>
```

## Why The Oyster Project Needs A Mount

The Astro Airflow project lives inside the main Oyster repository.

```text
oyster-journey-data-platform/
├── config/
├── data/
├── database/
├── dbt/
├── orchestration/
│   └── airflow/
│       ├── dags/
│       ├── include/
│       ├── plugins/
│       ├── tests/
│       └── docker-compose.override.yml
├── python/
├── README.md
└── requirements.txt
```

By default, the local Airflow containers only see the Astro project folders.

```text
/usr/local/airflow/
├── dags/
├── include/
├── plugins/
└── tests/
```

The Oyster DAG needs access to files outside the Airflow project folder.

```text
oyster-journey-data-platform/
├── config/
│   └── oyster_project.local.yml
├── data/
│   └── import/
│       └── oyster_journey/
├── database/
│   └── duckdb/
│       └── oyster.duckdb
├── dbt/
│   └── oyster_dbt/
└── python/
    └── ingestion/
        └── scripts/
            └── load_raw_oyster_journey_history_duckdb.py
```

The mount makes the wider repository visible inside the Airflow containers.

```text
/usr/local/airflow/
└── oyster_project/
    ├── config/
    ├── data/
    ├── database/
    ├── dbt/
    ├── orchestration/
    ├── python/
    ├── README.md
    └── requirements.txt
```

## Oyster Project Volume Mount

Create this file:

```text
oyster-journey-data-platform/
└── orchestration/
    └── airflow/
        └── docker-compose.override.yml
```

Add this content:

```yaml
services:
  api-server:
    volumes:
      - ../..:/usr/local/airflow/oyster_project

  scheduler:
    volumes:
      - ../..:/usr/local/airflow/oyster_project

  dag-processor:
    volumes:
      - ../..:/usr/local/airflow/oyster_project

  triggerer:
    volumes:
      - ../..:/usr/local/airflow/oyster_project
```

## Why This Differs From The Official Example

The official example is a minimal example. It shows the mount pattern using one folder, one service, and a read-only mount.

The Oyster project version adapts that pattern.

```text
Official example:
<absolute-host-path>:/usr/local/airflow/custom_dependencies:ro

Oyster project:
../..:/usr/local/airflow/oyster_project
```

The differences are:

| Difference | Reason |
|---|---|
| `../..` instead of an absolute path | Keeps the project portable when cloned to a different location |
| `/usr/local/airflow/oyster_project` instead of `custom_dependencies` | Makes the mounted path describe the Oyster project clearly |
| No `:ro` flag | The workflow may update `database/duckdb/oyster.duckdb` |
| Multiple Airflow services | The DAG-related services should see the same project files |

The relative path `../..` works because the override file is inside `orchestration/airflow`.

```text
oyster-journey-data-platform/      # Mounted by ../..
└── orchestration/
    └── airflow/
        └── docker-compose.override.yml
```

## How To Apply The Mount

Restart Astro after creating or changing the override file.

```bash
cd /Users/macbookpro/Documents/_dev2/oyster-journey-data-platform/orchestration/airflow
astro dev restart
```

## How To Test The Mount

From the Mac terminal, check that the wider project is visible inside the Airflow container.

```bash
docker exec airflow_de5c1e-api-server-1 ls /usr/local/airflow/oyster_project
```

Expected output should include the wider project folders.

```text
README.md
config
data
database
dbt
docs
jupyter_notebooks
logs
orchestration
python
requirements.txt
```

The container name can change after restarting Astro. To check the current container names, run:

```bash
astro dev ps
```

You can also open a shell inside the Airflow `api-server` container.

```bash
astro dev bash --api-server
```

or:

```bash
astro dev bash -a
```

Then run these checks inside the container.

```bash
test -f /usr/local/airflow/oyster_project/config/oyster_project.local.yml && echo "config found"
test -f /usr/local/airflow/oyster_project/database/duckdb/oyster.duckdb && echo "duckdb found"
test -d /usr/local/airflow/oyster_project/dbt/oyster_dbt && echo "dbt project found"
test -f /usr/local/airflow/oyster_project/python/ingestion/scripts/load_raw_oyster_journey_history_duckdb.py && echo "ingestion script found"
```

Expected output:

```text
config found
duckdb found
dbt project found
ingestion script found
```

Exit the container.

```bash
exit
```
