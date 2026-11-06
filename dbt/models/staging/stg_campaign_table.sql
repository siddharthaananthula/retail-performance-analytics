{{ config(materialized='view') }}

SELECT
    household_key,
    campaign AS campaign_id,
    TRIM(description) AS campaign_type
FROM {{ source('retail_raw', 'campaign_table') }}