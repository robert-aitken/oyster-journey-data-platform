from dataclasses import dataclass
from pathlib import Path
import pandas as pd
import duckdb


@dataclass
class OysterProjectPaths:
    project_root: Path
    import_path: Path
    csv_paths: list[Path]
    database_path: Path


def find_oyster_project_paths(start_path: Path) -> OysterProjectPaths:
    current_path = start_path.resolve()
    search_paths = [current_path]

    for parent_path in current_path.parents:
        search_paths.append(parent_path)

    for root_path in search_paths:
        import_path = root_path / "data" / "import" / "oyster_journey"
        database_dir = root_path / "database" / "duckdb"
        database_path = database_dir / "oyster.duckdb"

        if import_path.exists():
            database_dir.mkdir(parents=True, exist_ok=True)
            csv_paths = sorted(import_path.glob("*.csv"))
            if not csv_paths:
                raise ValueError(f"No CSV files found in import folder: {import_path}")

            return OysterProjectPaths(
                project_root=root_path,
                import_path=import_path,
                csv_paths=csv_paths,
                database_path=database_path,
            )

    raise FileNotFoundError(
        "Could not find project root. Expected to find data/import/oyster_journey "
        "in this folder or one of its parent folders."
    )


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

        # Print a few examples.
        # if len(raw_dfs) < 3:
        #     print(f"Sample csv_path.name, df_part.shape: {csv_path.name} {df_part.shape}")
        #     print(f"source_file: {df_part['source_file'].iloc[0]}")
        #     print(df_part.head(1).to_string())
        #     print("--------------------------------------------------")

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
    con: duckdb.DuckDBPyConnection, raw_df: pd.DataFrame
) -> None:
    con.register("raw_oyster_journey_df", raw_df)

    con.execute("CREATE SCHEMA IF NOT EXISTS oyster.raw")

    con.execute("""
    CREATE OR REPLACE TABLE oyster.raw.oyster_journey_history AS
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

    row_count = con.execute(
        "SELECT COUNT(*) FROM oyster.raw.oyster_journey_history"
    ).fetchone()[0]
    print(f"Rows loaded to oyster.raw.oyster_journey_history: {row_count}")


def print_raw_table_columns(con: duckdb.DuckDBPyConnection) -> None:
    raw_table_columns_df = con.execute("""
    SELECT 
        table_catalog,
        table_schema,
        table_name,
        column_name,
        ordinal_position,
        data_type
    FROM information_schema.columns
    WHERE table_catalog = 'oyster'
        AND table_schema = 'raw'
    ORDER BY
        table_catalog,
        table_schema,
        table_name,
        ordinal_position
    """).df()

    print("raw_table_columns_df:")
    print(raw_table_columns_df)
    print("--------------------------------------------------")


def print_raw_oyster_journey_history_sample(con: duckdb.DuckDBPyConnection) -> None:
    raw_oyster_journey_history_sample_df = con.execute("""
    SELECT *
    FROM oyster.raw.oyster_journey_history
    LIMIT 10
    """).df()

    print("raw_oyster_journey_history_sample_df:")
    print(raw_oyster_journey_history_sample_df)
    print("--------------------------------------------------")


# Entrypoint module: supports script and package runs.
def main() -> None:
    # Use this for a fixed project root if needed.
    # oyster_project_paths = find_oyster_project_paths(Path("/Users/macbookpro/Documents/_dev2/oyster-journey-data-platform"))
    oyster_project_paths = find_oyster_project_paths(Path.cwd())

    print("Import Path:", oyster_project_paths.import_path)

    raw_df = build_raw_oyster_journey_dataframe(oyster_project_paths.csv_paths)
    print("raw_df sample:")
    print(raw_df.head(10))

    print(f"database_path: {oyster_project_paths.database_path}")

    con = connect_to_duckdb(oyster_project_paths.database_path)
    load_raw_oyster_journey_history_table(con, raw_df)
    print_raw_table_columns(con)
    print_raw_oyster_journey_history_sample(con)

    con.close()


if __name__ == "__main__":
    main()
