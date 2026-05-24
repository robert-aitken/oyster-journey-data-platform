{{ config(
    materialized="table",
    schema="mart",
    tags=["OYSTER_JOURNEY"]
) }}

SELECT
    journey_day,
    journey_count,
    total_charge_pence,
    total_credit_pence
FROM {{ ref('int_oyster_daily_spend') }}
