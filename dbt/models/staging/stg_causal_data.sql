{{ config(materialized='view') }}

SELECT
    product_id,
    store_id,
    week_no,
    TRIM(display) AS display_code,
    TRIM(mailer) AS mailer_code
FROM {{ source('retail_raw', 'causal_data') }}