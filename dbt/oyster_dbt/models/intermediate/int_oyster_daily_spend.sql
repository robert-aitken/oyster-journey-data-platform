{{ config(
    materialized="table",
    schema="intermediate",
    tags=["OYSTER_JOURNEY"]
) }}

WITH CTE AS (
    SELECT
        CAST(COALESCE(CAST(start_date_time AS DATE), journey_date) AS DATE) AS journey_day,
        COUNT(*) AS journey_count,
        CAST(SUM(COALESCE(charge_pence, 0)) AS BIGINT) AS total_charge_pence,
        CAST(SUM(COALESCE(credit_pence, 0)) AS BIGINT) AS total_credit_pence
    FROM {{ ref('int_oyster_journey_events') }}
    GROUP BY
        journey_day
)

SELECT
    journey_day,
    journey_count,
    total_charge_pence,
    total_credit_pence
FROM CTE
