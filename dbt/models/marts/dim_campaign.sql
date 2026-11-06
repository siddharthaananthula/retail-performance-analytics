{{ config(materialized='view') }}

SELECT
    campaign_id,
    campaign_type,
    start_day,
    end_day
FROM {{ ref('stg_campaign_desc') }}