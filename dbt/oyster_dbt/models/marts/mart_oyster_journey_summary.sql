{{ config(
    materialized="table",
    schema="mart",
    tags=["OYSTER_JOURNEY"]
) }}

SELECT
    journey_date,
    start_time,
    end_time,
    start_date_time,
    end_date_time,
    journey_from,
    journey_to,
    journey_type_from,
    journey_type_to,
    journey_type,
    bus_route,
    account_event_type,
    journey_action,
    charge_pence,
    credit_pence,
    balance_pence,
    note,
    source_file,
    import_datetime
FROM {{ ref('int_oyster_journey_events') }}
