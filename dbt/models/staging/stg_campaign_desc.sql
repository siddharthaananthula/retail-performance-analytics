{{ config(materialized='view') }}

SELECT
    campaign AS campaign_id,
    TRIM(description) AS campaign_type,
    start_day,
    end_day
FROM {{ source('retail_raw', 'campaign_desc') }}