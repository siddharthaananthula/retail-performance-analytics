{{ config(materialized='table') }}

-- Collapse all causal states before exposing promotion data to reporting.
SELECT
    product_id,
    store_id,
    week_no,
    COUNT(*) AS source_state_count,
    COUNT(DISTINCT COALESCE(display_code, '<NULL>')) AS display_state_count,
    COUNT(DISTINCT COALESCE(mailer_code, '<NULL>')) AS mailer_state_count,
    BOOL_OR(COALESCE(display_code, '0') <> '0') AS has_display,
    BOOL_OR(COALESCE(mailer_code, '0') <> '0') AS has_mailer
FROM {{ ref('stg_causal_data') }}
GROUP BY product_id, store_id, week_no
