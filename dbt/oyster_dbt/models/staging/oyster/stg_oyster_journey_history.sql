{{ config(
    materialized="table",
    schema="staging",
    tags=["OYSTER_JOURNEY"]
) }}

WITH CTE AS (
    SELECT
        NULLIF(TRIM(journey_date), '') AS journey_date,
        NULLIF(TRIM(start_time), '') AS start_time,
        NULLIF(TRIM(end_time), '') AS end_time,
        NULLIF(TRIM(journey_action), '') AS journey_action,
        NULLIF(TRIM(charge), '') AS charge,
        NULLIF(TRIM(credit), '') AS credit,
        NULLIF(TRIM(balance), '') AS balance,
        NULLIF(TRIM(note), '') AS note,
        NULLIF(TRIM(source_file), '') AS source_file,
        import_datetime
    FROM {{ source('raw', 'oyster_journey_history') }}
)

SELECT
    journey_date,
    start_time,
    end_time,
    journey_action,
    charge,
    credit,
    balance,
    note,
    source_file,
    import_datetime
FROM CTE
