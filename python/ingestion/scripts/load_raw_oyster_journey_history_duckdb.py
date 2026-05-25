import argparse
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd
import yaml


@dataclass
class OysterProjectConfig:
    project_root: Path
    config_path: Path
    project_name: str
    project_mode: str
    import_path: Path
    csv_paths: list[Path]
    database_path: Path
    database_name: str
    raw_schema: str
    raw_table: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load Oyster journey CSV files into DuckDB."
    )
    parser.add_argument(
        "--config-path",
        default="config/oyster_project.sample.yml",
        help="Path to the Oyster project config YAML file.",
    )
    return parser.parse_args()


def find_project_root(start_path: Path) -> Path:
    current_path = start_path.resolve()
    search_paths = [current_path, *current_path.parents]

    for root_path in search_paths:
        if (
            (root_path / ".gitignore").exists()
            and (root_path / "python").exists()
            and (root_path / "dbt").exists()
            and (root_path / "config").exists()
        ):
            return root_path

    raise FileNotFoundError(
        "Could not find project root. Expected to find .gitignore, python, dbt, "
        "and config in this folder or one of its parent folders."
    )


def validate_oyster_project_config(config_data: dict) -> None:
    if not isinstance(config_data, dict):
        raise ValueError("Config file must contain a top-level dictionary.")

    required_keys = [
        ("project", "name"),
        ("project", "mode"),
        ("paths", "import_path"),
        ("paths", "database_path"),
        ("duckdb", "database_name"),
        ("duckdb", "raw_schema"),
        ("duckdb", "raw_table"),
    ]

    for section_name, key_name in required_keys:
        section = config_data.get(section_name)
        if not isinstance(section, dict):
            raise ValueError(f"Missing required config section: {section_name}")

        value = section.get(key_name)
        if value is None:
            raise ValueError(f"Missing required config key: {section_name}.{key_name}")

    for section_name, key_name in [
        ("duckdb", "database_name"),
        ("duckdb", "raw_schema"),
        ("duckdb", "raw_table"),
    ]:
        value = config_data[section_name][key_name]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Config value must be a non-empty string: {section_name}.{key_name}"
            )


def load_oyster_project_config(
    project_root: Path, config_path_arg: str
) -> OysterProjectConfig:
    config_path = Path(config_path_arg)
    if not config_path.is_absolute():
        config_path = project_root / config_path
    config_path = config_path.resolve()

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        config_data = yaml.safe_load(config_file)

    validate_oyster_project_config(config_data)

    import_path = Path(config_data["paths"]["import_path"])
    if not import_path.is_absolute():
        import_path = project_root / import_path
    import_path = import_path.resolve()

    if not import_path.exists():
        raise FileNotFoundError(f"Import folder does not exist: {import_path}")

    csv_paths = sorted(import_path.glob("*.csv"))
    if not csv_paths:
        raise ValueError(f"No CSV files found in import folder: {import_path}")

    database_path = Path(config_data["paths"]["database_path"])
    if not database_path.is_absolute():
        database_path = project_root / database_path
    database_path = database_path.resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)

    return OysterProjectConfig(
        project_root=project_root,
        config_path=config_path,
        project_name=config_data["project"]["name"],
        project_mode=config_data["project"]["mode"],
        import_path=import_path,
        csv_paths=csv_paths,
        database_path=database_path,
        database_name=config_data["duckdb"]["database_name"].strip(),
        raw_schema=config_data["duckdb"]["raw_schema"].strip(),
        raw_table=config_data["duckdb"]["raw_table"].strip(),
    )


def build_duckdb_target_table_sql(
    database_name: str, raw_schema: str, raw_table: str
) -> str:
    return f"{database_name}.{raw_schema}.{raw_table}"


def build_raw_oyster_journey_dataframe(csv_paths: list[Path]) -> pd.DataFrame:
    # Handle empty files, blank rows, header-only files, and read errors.
    raw_dfs: list[pd.DataFrame] = []
    skipped_files = 0
    skipped_errors = 0

    for csv_path in csv_paths:
        if csv_path.stat().st_size == 0:
            skipped_files += 1
            print(f"skipped_files: {skipped_files} {csv_path} (reason: file size is 0)")
            continue

        try:
            df_part = pd.read_csv(csv_path)
        except pd.errors.EmptyDataError:
            skipped_files += 1
            print(
                f"skipped_files: {skipped_files} {csv_path} (reason: csv has no rows)"
            )
            continue
        except Exception as exc:
            skipped_errors += 1
            print(f"skipped_error: {csv_path.name} ({type(exc).__name__}: {exc})")
            continue

        if df_part.empty:
            skipped_files += 1
            print(
                f"skipped_files: {skipped_files} {csv_path} (reason: csv has header but no rows)"
            )
            continue

        df_part["source_file"] = csv_path.name
        raw_dfs.append(df_part)

    # If raw_dfs has at least one dataframe, concatenate them into one raw_df.
    # If raw_dfs is empty, create an empty dataframe instead to prevent error.
    if raw_dfs:
        raw_df = pd.concat(raw_dfs, ignore_index=True)
    else:
        raw_df = pd.DataFrame()

    print(f"Dataframes collected: {len(raw_dfs)}")

    # Rename source CSV columns to database-friendly raw column names.
    raw_df = raw_df.rename(
        columns={
            "Date": "journey_date",
            "Start Time": "start_time",
            "End Time": "end_time",
            "Journey/Action": "journey_action",
            "Charge": "charge",
            "Credit": "credit",
            "Balance": "balance",
            "Note": "note",
        }
    )

    # Set the dataframe columns left to right.
    raw_df = raw_df.reindex(
        columns=[
            "journey_date",
            "start_time",
            "end_time",
            "journey_action",
            "charge",
            "credit",
            "balance",
            "note",
            "source_file",
        ]
    )

    print(f"Rows in raw_df: {len(raw_df)}")
    print(f"Skipped files: {skipped_files}")
    print(f"Skipped errors: {skipped_errors}")

    return raw_df


def connect_to_duckdb(database_path: Path) -> duckdb.DuckDBPyConnection:
    database_already_exists = database_path.exists()

    if database_already_exists:
        print(f"Database found: {database_path}")
    else:
        print(f"Database not found. Creating: {database_path}")

    con = duckdb.connect(str(database_path), read_only=False)

    if database_path.exists():
        print(f"Database ready: {database_path}")

    duckdb_context_sql = """
    SELECT
        CURRENT_DATABASE() AS database_name,
        CURRENT_SCHEMA() AS schema_name,
        VERSION() AS duckdb_version
    """

    duckdb_connection_context_df = con.execute(duckdb_context_sql).df()

    print("--------------------------------------------------")
    print(duckdb_connection_context_df)
    print("--------------------------------------------------")

    return con


def load_raw_oyster_journey_history_table(
    con: duckdb.DuckDBPyConnection,
    raw_df: pd.DataFrame,
    project_config: OysterProjectConfig,
) -> int:
    con.register("raw_oyster_journey_df", raw_df)

    target_schema_sql = f"{project_config.database_name}.{project_config.raw_schema}"
    target_table_sql = build_duckdb_target_table_sql(
        project_config.database_name,
        project_config.raw_schema,
        project_config.raw_table,
    )

    con.execute(f"CREATE SCHEMA IF NOT EXISTS {target_schema_sql}")

    con.execute(f"""
    CREATE OR REPLACE TABLE {target_table_sql} AS
    SELECT
        CAST(journey_date AS VARCHAR) AS journey_date,
        CAST(start_time AS VARCHAR) AS start_time,
        CAST(end_time AS VARCHAR) AS end_time,
        CAST(journey_action AS VARCHAR) AS journey_action,
        CAST(charge AS VARCHAR) AS charge,
        CAST(credit AS VARCHAR) AS credit,
        CAST(balance AS VARCHAR) AS balance,
        CAST(note AS VARCHAR) AS note,
        CAST(source_file AS VARCHAR) AS source_file,
        CURRENT_TIMESTAMP AS import_datetime
    FROM raw_oyster_journey_df
    """)

    row_count = con.execute(f"SELECT COUNT(*) FROM {target_table_sql}").fetchone()[0]
    print(f"Rows loaded to {target_table_sql}: {row_count}")
    return row_count


def print_raw_table_columns(
    con: duckdb.DuckDBPyConnection, project_config: OysterProjectConfig
) -> None:
    raw_table_columns_df = con.execute(f"""
    SELECT
        table_catalog,
        table_schema,
        table_name,
        column_name,
        ordinal_position,
        data_type
    FROM information_schema.columns
    WHERE table_catalog = '{project_config.database_name}'
        AND table_schema = '{project_config.raw_schema}'
        AND table_name = '{project_config.raw_table}'
    ORDER BY
        table_catalog,
        table_schema,
        table_name,
        ordinal_position
    """).df()

    print("raw_table_columns_df:")
    print(raw_table_columns_df)
    print("--------------------------------------------------")


def print_raw_oyster_journey_history_sample(
    con: duckdb.DuckDBPyConnection, project_config: OysterProjectConfig
) -> None:
    target_table_sql = build_duckdb_target_table_sql(
        project_config.database_name,
        project_config.raw_schema,
        project_config.raw_table,
    )

    raw_oyster_journey_history_sample_df = con.execute(f"""
    SELECT *
    FROM {target_table_sql}
    LIMIT 10
    """).df()

    print("raw_oyster_journey_history_sample_df:")
    print(raw_oyster_journey_history_sample_df)
    print("--------------------------------------------------")


# Entrypoint module: supports script and package runs.
def main() -> None:
    args = parse_args()
    project_root = find_project_root(Path.cwd())
    project_config = load_oyster_project_config(project_root, args.config_path)
    target_table_sql = build_duckdb_target_table_sql(
        project_config.database_name,
        project_config.raw_schema,
        project_config.raw_table,
    )

    print(f"Project root: {project_config.project_root}")
    print(f"Config path: {project_config.config_path}")
    print(f"Project mode: {project_config.project_mode}")
    print(f"Import path: {project_config.import_path}")
    print(f"CSV files found: {len(project_config.csv_paths)}")
    print(f"Database path: {project_config.database_path}")
    print(f"DuckDB target table: {target_table_sql}")

    raw_df = build_raw_oyster_journey_dataframe(project_config.csv_paths)
    print("raw_df sample:")
    print(raw_df.head(10))

    con = connect_to_duckdb(project_config.database_path)
    load_raw_oyster_journey_history_table(con, raw_df, project_config)
    print_raw_table_columns(con, project_config)
    print_raw_oyster_journey_history_sample(con, project_config)
    con.close()


if __name__ == "__main__":
    main()
