{{ config(
    materialized="table",
    schema="intermediate",
    tags=["OYSTER_JOURNEY"]
) }}

WITH CTE AS (
    SELECT
        CASE
            WHEN journey_date IS NULL THEN NULL
            ELSE CAST(STRPTIME(journey_date, '%d-%b-%Y') AS DATE)
        END AS journey_date,
        CASE
            WHEN start_time IS NULL THEN NULL
            ELSE CAST(STRPTIME(start_time, '%H:%M') AS TIME)
        END AS start_time,
        CASE
            WHEN end_time IS NULL THEN NULL
            ELSE CAST(STRPTIME(end_time, '%H:%M') AS TIME)
        END AS end_time,
        CASE
            WHEN start_time IS NULL OR journey_date IS NULL THEN NULL
            ELSE STRPTIME(journey_date || ' ' || start_time, '%d-%b-%Y %H:%M')
        END AS start_date_time,
        CASE
            WHEN end_time IS NULL OR journey_date IS NULL THEN NULL
            ELSE STRPTIME(journey_date || ' ' || end_time, '%d-%b-%Y %H:%M')
        END AS end_date_time,
        CASE
            WHEN REGEXP_MATCHES(journey_action, '(?i) to ') THEN CAST(NULLIF({{ clean_location_name("NULLIF(TRIM(REGEXP_EXTRACT(journey_action, '(?i)^(.*?) to .*$', 1)), '')") }}, '') AS VARCHAR)
            ELSE NULL
        END AS journey_from,
        CASE
            WHEN REGEXP_MATCHES(journey_action, '(?i) to ') THEN CAST(NULLIF({{ clean_location_name("NULLIF(TRIM(REGEXP_EXTRACT(journey_action, '(?i)^.*? to (.*)$', 1)), '')") }}, '') AS VARCHAR)
            ELSE NULL
        END AS journey_to,
        CASE
            WHEN REGEXP_MATCHES(journey_action, '(?i) to ') THEN COALESCE(
                NULLIF(TRIM(REGEXP_EXTRACT(NULLIF(TRIM(REGEXP_EXTRACT(journey_action, '(?i)^(.*?) to .*$', 1)), ''), '\\[(.*?)\\]', 1)), ''),
                NULLIF(TRIM(REGEXP_EXTRACT(NULLIF(TRIM(REGEXP_EXTRACT(journey_action, '(?i)^(.*?) to .*$', 1)), ''), '\\((.*?)\\)', 1)), ''),
                'London Underground'
            )
            ELSE NULL
        END AS journey_type_from,
        CASE
            WHEN REGEXP_MATCHES(journey_action, '(?i) to ') THEN COALESCE(
                NULLIF(TRIM(REGEXP_EXTRACT(NULLIF(TRIM(REGEXP_EXTRACT(journey_action, '(?i)^.*? to (.*)$', 1)), ''), '\\[(.*?)\\]', 1)), ''),
                NULLIF(TRIM(REGEXP_EXTRACT(NULLIF(TRIM(REGEXP_EXTRACT(journey_action, '(?i)^.*? to (.*)$', 1)), ''), '\\((.*?)\\)', 1)), ''),
                'London Underground'
            )
            ELSE NULL
        END AS journey_type_to,
        CASE
            WHEN journey_action ILIKE '%bus journey%' THEN 'Bus'
            WHEN REGEXP_MATCHES(journey_action, '(?i) to ') THEN 'Train or Underground'
            ELSE 'Other'
        END AS journey_type,
        CASE
            WHEN journey_action ILIKE '%bus journey%' THEN NULLIF(TRIM(SPLIT_PART(journey_action, 'route ', 2)), '')
            ELSE NULL
        END AS bus_route,
        CASE
            WHEN journey_action ILIKE '%topped up%' THEN 'Top Up'
            WHEN credit IS NOT NULL THEN 'credit'
            ELSE NULL
        END AS account_event_type,
        CAST(journey_action AS VARCHAR) AS journey_action,
        CAST({{ pence_from_amount('charge') }} AS BIGINT) AS charge_pence,
        CAST({{ pence_from_amount('credit') }} AS BIGINT) AS credit_pence,
        CAST({{ pence_from_amount('balance') }} AS BIGINT) AS balance_pence,
        CAST(note AS VARCHAR) AS note,
        CAST(source_file AS VARCHAR) AS source_file,
        CAST(import_datetime AS TIMESTAMPTZ) AS import_datetime
    FROM {{ ref('stg_oyster_journey_history') }}
)

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
FROM CTE
