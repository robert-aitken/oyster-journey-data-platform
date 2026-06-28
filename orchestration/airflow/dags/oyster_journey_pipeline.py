from pathlib import Path

from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag, task
from pendulum import datetime


@dag(
    dag_id="oyster_journey_pipeline",
    description="Orchestrates the local Oyster journey ingestion and dbt build workflow.",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["oyster"],
)
def oyster_journey_pipeline():
    start_task = EmptyOperator(task_id="start")

    @task(task_id="check_required_paths")
    def check_required_paths() -> None:
        oyster_project_root = Path("/usr/local/airflow/oyster_project")

        required_paths = {
            "Oyster project root": oyster_project_root,
            "Config file": oyster_project_root / "config/oyster_project.local.yml",
            "Import folder": oyster_project_root / "data/import/oyster_journey",
            "DuckDB folder": oyster_project_root / "database/duckdb",
            "Ingestion script": oyster_project_root
            / "python/ingestion/scripts/load_raw_oyster_journey_history_duckdb.py",
            "dbt project": oyster_project_root / "dbt/oyster_dbt",
            "dbt profiles file": oyster_project_root
            / "dbt/oyster_dbt/profiles/profiles.yml",
        }

        missing_paths = []

        for path_description, required_path in required_paths.items():
            if required_path.exists():
                print(f"{path_description} found: {required_path}")
            else:
                missing_paths.append(f"{path_description}: {required_path}")

        if missing_paths:
            missing_path_text = "\n".join(missing_paths)
            raise FileNotFoundError(
                "One or more required Oyster paths were not found:\n"
                f"{missing_path_text}"
            )

        print("All required Oyster paths were found.")

    check_required_paths_task = check_required_paths()

    load_raw_oyster_journey_history_task = BashOperator(
        task_id="load_raw_oyster_journey_history_duckdb",
        bash_command=(
            "cd /usr/local/airflow/oyster_project && "
            "python python/ingestion/scripts/load_raw_oyster_journey_history_duckdb.py "
            "--config-path config/oyster_project.local.yml"
        ),
    )

    run_oyster_journey_dbt_build_task = BashOperator(
        task_id="run_oyster_journey_dbt_build",
        bash_command=(
            "cd /usr/local/airflow/oyster_project/dbt/oyster_dbt && "
            "dbt build --profiles-dir profiles --select tag:OYSTER_JOURNEY"
        ),
    )

    end_task = EmptyOperator(task_id="end")

    (
        start_task
        >> check_required_paths_task
        >> load_raw_oyster_journey_history_task
        >> run_oyster_journey_dbt_build_task
        >> end_task
    )


oyster_journey_pipeline()
